import uuid
from typing import TYPE_CHECKING, List

from aioredis import Redis
from fastapi import Depends
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED

from fastapi_admin2 import constants
from fastapi_admin2.base.entities import AbstractAdmin
from fastapi_admin2.depends import get_current_admin, get_resources
from fastapi_admin2.i18n import lazy_gettext as _
from fastapi_admin2.providers import Provider
from fastapi_admin2.providers.security.dependencies import AdminDaoDependencyMarker, EntityNotFound, \
    AdminDaoProto
from fastapi_admin2.providers.security.dto import InitAdmin, RenewPasswordForm
from fastapi_admin2.providers.security.password_hasher import PasswordHasherProto, Argon2PasswordHasher, \
    HashingFailedError
from fastapi_admin2.template import templates
from fastapi_admin2.utils.depends import get_dependency_from_request_by_marker
from fastapi_admin2.utils.file_upload import FileUploader

if TYPE_CHECKING:
    from fastapi_admin2.app import FastAPIAdmin


class SecurityProvider(Provider):
    name = "security_provider"

    access_token_key = "access_token"

    def __init__(
            self,
            avatar_uploader: FileUploader,
            redis: Redis,
            password_hasher: PasswordHasherProto = Argon2PasswordHasher(),
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
        self._avatar_uploader = avatar_uploader
        self._redis_client = redis

    async def login_view(self, request: Request):
        return templates.TemplateResponse(
            self.template,
            context={
                "request": request,
                "login_logo_url": self.login_logo_url,
                "login_title": self.login_title_translation_key,
            },
        )

    def register(self, app: "FastAPIAdmin"):
        super(SecurityProvider, self).register(app)
        login_path = self.login_path
        app.get(login_path)(self.login_view)
        app.post(login_path)(self.login)
        app.get(self.logout_path)(self.logout)
        app.middleware("http")(self.authenticate)
        app.get("/init")(self.init_view)
        app.post("/init")(self.handle_creation_of_init_admin)
        app.get("/renew_password")(self.password_view)
        app.post("/renew_password")(self.renew_password)

    async def login(
            self,
            request: Request,
            user_repository: AdminDaoProto = Depends(AdminDaoDependencyMarker)
    ) -> Response:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        remember_me = form.get("remember_me")
        unauthorized_response = templates.TemplateResponse(
            self.template,
            status_code=HTTP_401_UNAUTHORIZED,
            context={"request": request, "error": _("login_failed")},
        )
        try:
            admin = await user_repository.get_one_admin_by_filters(username=username)
        except EntityNotFound:
            return unauthorized_response
        else:
            if await self._password_hash_is_invalid(user_repository, admin, password):
                return unauthorized_response

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
        )
        await self._redis_client.set(constants.LOGIN_USER.format(token=token), admin.id, ex=expire)
        return response

    async def logout(self, request: Request) -> Response:
        response = self.redirect_login(request)
        response.delete_cookie(self.access_token_key, path=request.app.admin_path)
        token = request.cookies.get(self.access_token_key)
        await self._redis_client.delete(constants.LOGIN_USER.format(token=token))
        return response

    async def authenticate(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        admin_repository = get_dependency_from_request_by_marker(request, AdminDaoDependencyMarker)

        token = request.cookies.get(self.access_token_key)
        path = request.scope["path"]
        admin = None
        if token:
            token_key = constants.LOGIN_USER.format(token=token)
            admin_id = int(await self._redis_client.get(token_key))
            try:
                admin = await admin_repository.get_one_admin_by_filters(id=admin_id)
            except EntityNotFound:
                pass
        request.state.admin = admin

        if path == self.login_path and admin:
            return RedirectResponse(url=request.app.admin_path, status_code=HTTP_303_SEE_OTHER)

        response = await call_next(request)
        return response

    async def init_view(
            self,
            request: Request,
            user_repository: AdminDaoProto = Depends(AdminDaoDependencyMarker)
    ) -> Response:
        if await user_repository.is_exists_at_least_one_admin():
            return self.redirect_login(request)
        return templates.TemplateResponse("init.html", context={"request": request})

    async def handle_creation_of_init_admin(
            self,
            request: Request,
            init_admin: InitAdmin = Depends(InitAdmin),
            admin_repository: AdminDaoProto = Depends(
                AdminDaoDependencyMarker
            )
    ):
        if await admin_repository.is_exists_at_least_one_admin():
            return self.redirect_login(request)

        if init_admin.password != init_admin.confirm_password:
            return templates.TemplateResponse(
                "init.html",
                context={"request": request, "error": _("confirm_password_different")},
            )

        path_to_avatar_image = await self._avatar_uploader.upload(init_admin.avatar)

        await admin_repository.add_admin(
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
            user_repository: AdminDaoProto = Depends(AdminDaoDependencyMarker)
    ) -> Response:
        error = None
        if self._password_hash_is_invalid(user_repository, admin, renew_password_form.old_password):
            error = _("old_password_error")

        if renew_password_form.new_password != renew_password_form.re_new_password:
            error = _("new_password_different")

        if error:
            return templates.TemplateResponse(
                "renew_password.html",
                context={"request": request, "resources": resources, "error": error},
            )

        await user_repository.update_admin({"id": admin.id}, password=renew_password_form.new_password)
        return await self.logout(request)

    async def _password_hash_is_invalid(
            self,
            user_repository: AdminDaoProto,
            admin: AbstractAdmin,
            password: str
    ) -> bool:
        try:
            self._password_hasher.verify(admin.password, password)
        except HashingFailedError:
            return True

        if self._password_hasher.is_rehashing_required(admin.password):
            await user_repository.update_admin({}, password=self._password_hasher.hash(admin.password))

        return False
