import uuid
from typing import TYPE_CHECKING, List

from aioredis import Redis
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from fastapi import Depends, Form
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED

from fastapi_admin import constants
from fastapi_admin.database.models.abstract import Admin
from fastapi_admin.database.repository.admin import UserRepositoryProto, AdministratorNotFound
from fastapi_admin.depends import get_current_admin, get_resources
from fastapi_admin.providers import Provider
from fastapi_admin.providers.security.dependencies import UserRepositoryDependencyMarker, \
    RedisClientDependencyMarker
from fastapi_admin.providers.security.dto import InitAdmin
from fastapi_admin.services.file_upload import FileUploader
from fastapi_admin.services.i18n.context import lazy_gettext as _
from fastapi_admin.template import templates
from fastapi_admin.utils.depends import get_dependency_from_request_by_marker

if TYPE_CHECKING:
    from fastapi_admin.app import FastAPIAdmin


class SecurityProvider(Provider):
    name = "security_provider"

    access_token_key = "access_token"

    def __init__(
            self,
            avatar_uploader: FileUploader,
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
        self._password_hasher = PasswordHasher()
        self._avatar_uploader = avatar_uploader

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
            user_repository: UserRepositoryProto = Depends(UserRepositoryDependencyMarker),
            redis: Redis = Depends(RedisClientDependencyMarker)
    ):
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
        except AdministratorNotFound:
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
        await redis.set(constants.LOGIN_USER.format(token=token), admin.id, ex=expire)
        return response

    async def logout(self, request: Request):
        response = self.redirect_login(request)
        response.delete_cookie(self.access_token_key, path=request.app.admin_path)
        token = request.cookies.get(self.access_token_key)
        await request.app.redis.delete(constants.LOGIN_USER.format(token=token))
        return response

    async def authenticate(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ):
        user_repository = get_dependency_from_request_by_marker(request, UserRepositoryDependencyMarker)
        redis = get_dependency_from_request_by_marker(request, RedisClientDependencyMarker)

        token = request.cookies.get(self.access_token_key)
        path = request.scope["path"]
        admin = None
        if token:
            token_key = constants.LOGIN_USER.format(token=token)
            admin_id = int(await redis.get(token_key))
            try:
                admin = await user_repository.get_one_admin_by_filters(id=admin_id)
            except AdministratorNotFound:
                pass
        request.state.admin = admin

        if path == self.login_path and admin:
            return RedirectResponse(url=request.app.admin_path, status_code=HTTP_303_SEE_OTHER)

        response = await call_next(request)
        return response

    async def init_view(
            self,
            request: Request,
            user_repository: UserRepositoryProto = Depends(UserRepositoryDependencyMarker)
    ):
        if await user_repository.is_exists_at_least_one_admin():
            return self.redirect_login(request)
        return templates.TemplateResponse("init.html", context={"request": request})

    async def handle_creation_of_init_admin(
            self,
            request: Request,
            init_admin: InitAdmin = Depends(InitAdmin),
            user_repository: UserRepositoryProto = Depends(
                UserRepositoryDependencyMarker
            )
    ):
        if await user_repository.is_exists_at_least_one_admin():
            return self.redirect_login(request)

        if init_admin.password != init_admin.confirm_password:
            return templates.TemplateResponse(
                "init.html",
                context={"request": request, "error": _("confirm_password_different")},
            )

        path_to_avatar_image = await self._avatar_uploader.upload(init_admin.avatar)

        await user_repository.add_user(
            username=init_admin.username,
            password=self._password_hasher.hash(init_admin.password),
            avatar=path_to_avatar_image
        )

        return self.redirect_login(request)

    def redirect_login(self, request: Request):
        return RedirectResponse(
            url=request.app.admin_path + self.login_path, status_code=HTTP_303_SEE_OTHER
        )

    async def password_view(
            self,
            request: Request,
            resources=Depends(get_resources),
    ):
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
            old_password: str = Form(...),
            new_password: str = Form(...),
            re_new_password: str = Form(...),
            admin: Admin = Depends(get_current_admin),
            resources: List[dict] = Depends(get_resources),
            user_repository: UserRepositoryProto = Depends(UserRepositoryDependencyMarker)
    ):
        error = None
        if self._password_hash_is_invalid(user_repository, admin, old_password):
            error = _("old_password_error")

        if new_password != re_new_password:
            error = _("new_password_different")

        if error:
            return templates.TemplateResponse(
                "renew_password.html",
                context={"request": request, "resources": resources, "error": error},
            )

        await user_repository.update_admin({"id": admin.id}, password=new_password)
        return await self.logout(request)

    async def _password_hash_is_invalid(
            self,
            user_repository: UserRepositoryProto,
            admin: Admin,
            password: str
    ) -> bool:
        try:
            self._password_hasher.verify(admin.password, password)
        except (InvalidHash, VerifyMismatchError):
            return True
        except AttributeError:  # if something wrong with password format
            return True

        if self._password_hasher.check_needs_rehash(admin.password):
            await user_repository.update_admin({}, password=self._password_hasher.hash(admin.password))

        return False
