import uuid
from typing import TYPE_CHECKING, List

from aioredis import Redis
from fastapi import Depends, HTTPException
from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED
from starlette.templating import Jinja2Templates

from fastapi_admin2 import constants
from fastapi_admin2.base.entities import AbstractAdmin
from fastapi_admin2.depends import get_resources
from fastapi_admin2.providers import Provider
from fastapi_admin2.providers.security.dependencies import AdminDaoDependencyMarker, EntityNotFound, \
    AdminDaoProto
from fastapi_admin2.providers.security.dto import InitAdmin, RenewPasswordForm
from fastapi_admin2.providers.security.password_hashing.protocol import HashVerifyFailedError, \
    PasswordHasherProto
from fastapi_admin2.utils.depends import get_dependency_from_request_by_marker
from fastapi_admin2.utils.files import FileManager

if TYPE_CHECKING:
    from fastapi_admin2.app import FastAPIAdmin


def get_current_admin(request: Request) -> AbstractAdmin:
    admin = request.state.admin
    if not admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    return admin


class SecurityProvider(Provider):
    name = "security_provider"

    access_token_key = "access_token"

    def __init__(
            self,
            file_manager: FileManager,
            redis: Redis,
            password_hasher: PasswordHasherProto,
            login_path: str = "/login",
            logout_path: str = "/logout",
            template: str = "providers/login/login.html",
            login_logo_url: str = None,
            login_title_translation_key: str = "login_title"
    ):
        self.login_path = login_path
        self.logout_path = logout_path
        self.template = template
        self.login_title_translation_key = login_title_translation_key
        self.login_logo_url = login_logo_url
        self._password_hasher = password_hasher
        self._avatar_uploader = file_manager
        self._redis = redis

    async def login_view(self, request: Request,
                         templates: Jinja2Templates = Depends(Jinja2Templates)) -> Response:
        return templates.TemplateResponse(
            self.template,
            context={
                "request": request,
                "login_logo_url": self.login_logo_url,
                "login_title": self.login_title_translation_key,
            },
        )

    def register(self, app: "FastAPIAdmin") -> None:
        super(SecurityProvider, self).register(app)
        login_path = self.login_path
        app.get(login_path)(self.login_view)
        app.post(login_path)(self.login)
        app.get(self.logout_path)(self.logout)
        app.get("/init")(self.init_view)
        app.post("/init")(self.handle_creation_of_init_admin)
        app.get("/renew_password")(self.password_view)
        app.post("/renew_password")(self.renew_password)

        app.add_middleware(BaseHTTPMiddleware, dispatch=self.authenticate)

    async def login(
            self,
            request: Request,
            admin_dao: AdminDaoProto = Depends(AdminDaoDependencyMarker),
            templates: Jinja2Templates = Depends(Jinja2Templates)
    ) -> Response:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        remember_me = form.get("remember_me")

        unauthorized_response = templates.TemplateResponse(
            self.template,
            status_code=HTTP_401_UNAUTHORIZED,
            context={"request": request, "error": request.state.t("login_failed")},
        )
        try:
            admin = await admin_dao.get_one_admin_by_filters(username=username)
        except EntityNotFound:
            return unauthorized_response
        else:
            if self._is_password_hash_is_invalid(admin, password):
                return unauthorized_response

            if self._password_hasher.is_rehashing_required(admin.password):
                await admin_dao.update_admin({}, password=self._password_hasher.hash(admin.password))

        response = RedirectResponse(url=request.app.admin_path, status_code=HTTP_303_SEE_OTHER)
        if remember_me == "on":
            expire = 3600 * 24 * 30
            response.set_cookie("remember_me", "on")
        else:
            expire = 3600
            response.delete_cookie("remember_me")

        token = uuid.uuid4().hex
        response.set_cookie(
            self.access_token_key,
            token,
            expires=expire,
            path=request.app.admin_path,
            httponly=True,
            samesite="Strict"
        )
        await self._redis.set(constants.LOGIN_USER.format(token=token), admin.id, ex=expire)
        return response

    async def logout(self, request: Request) -> Response:
        response = self.redirect_login(request)
        response.delete_cookie(self.access_token_key, path=request.app.admin_path)
        token = request.cookies.get(self.access_token_key)
        await self._redis.delete(constants.LOGIN_USER.format(token=token))
        return response

    async def authenticate(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.admin = None

        admin_dao: AdminDaoProto = get_dependency_from_request_by_marker(request, AdminDaoDependencyMarker)

        access_token = request.cookies.get(self.access_token_key)
        if not access_token:
            return await call_next(request)

        token_key = constants.LOGIN_USER.format(token=access_token)
        admin_id = await self._redis.get(token_key)
        try:
            admin = await admin_dao.get_one_admin_by_filters(id=int(admin_id))
        except (EntityNotFound, TypeError):
            return await call_next(request)

        request.state.admin = admin

        if request.scope["path"] == self.login_path:
            return RedirectResponse(url=request.app.admin_path, status_code=HTTP_303_SEE_OTHER)

        response = await call_next(request)
        return response

    async def init_view(
            self,
            request: Request,
            user_repository: AdminDaoProto = Depends(AdminDaoDependencyMarker),
            templates: Jinja2Templates = Depends(Jinja2Templates)
    ) -> Response:
        if await user_repository.is_exists_at_least_one_admin():
            return self.redirect_login(request)
        return templates.TemplateResponse("init.html", context={"request": request})

    async def handle_creation_of_init_admin(
            self,
            request: Request,
            init_admin: InitAdmin = Depends(InitAdmin),
            admin_dao: AdminDaoProto = Depends(
                AdminDaoDependencyMarker
            ),
            templates: Jinja2Templates = Depends(Jinja2Templates)
    ):
        if await admin_dao.is_exists_at_least_one_admin():
            return self.redirect_login(request)

        if init_admin.password != init_admin.confirm_password:
            return templates.TemplateResponse(
                "init.html",
                context={"request": request, "error": request.state.t("confirm_password_different")},
            )

        path_to_avatar_image = await self._avatar_uploader.upload(init_admin.avatar)

        await admin_dao.add_admin(
            username=init_admin.username,
            password=self._password_hasher.hash(init_admin.password),
            avatar=str(path_to_avatar_image)
        )

        return self.redirect_login(request)

    def redirect_login(self, request: Request) -> Response:
        return RedirectResponse(
            url=request.app.admin_path + self.login_path, status_code=HTTP_303_SEE_OTHER
        )

    async def password_view(
            self,
            request: Request,
            resources=Depends(get_resources),
            templates: Jinja2Templates = Depends(Jinja2Templates)
    ) -> Response:
        return templates.TemplateResponse(
            "providers/login/renew_password.html",
            context={
                "request": request,
                "resources": resources,
            },
        )

    async def renew_password(
            self,
            request: Request,
            renew_password_form: RenewPasswordForm,
            admin: AbstractAdmin = Depends(get_current_admin),
            resources: List[dict] = Depends(get_resources),
            admin_dao: AdminDaoProto = Depends(AdminDaoDependencyMarker),
            templates: Jinja2Templates = Depends(Jinja2Templates)
    ) -> Response:
        error = None
        if self._is_password_hash_is_invalid(admin, renew_password_form.old_password):
            error = request.state.t("old_password_error")

        if renew_password_form.new_password != renew_password_form.re_new_password:
            error = request.state.t("new_password_different")

        if error:
            return templates.TemplateResponse(
                "renew_password.html",
                context={"request": request, "resources": resources, "error": error},
            )

        await admin_dao.update_admin({"id": admin.id}, password=renew_password_form.new_password)
        return await self.logout(request)

    def _is_password_hash_is_invalid(
            self,
            admin: AbstractAdmin,
            password: str
    ) -> bool:
        try:
            self._password_hasher.verify(admin.password, password)
        except HashVerifyFailedError:
            return True

        return False
