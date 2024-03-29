import uuid
from typing import TYPE_CHECKING, List, Optional

from aioredis import Redis
from fastapi import Depends, HTTPException
from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.status import HTTP_303_SEE_OTHER, HTTP_401_UNAUTHORIZED

from fastapi_admin2.depends import get_resources
from fastapi_admin2.entities import AbstractAdmin
from fastapi_admin2.providers import Provider
from fastapi_admin2.providers.security.dependencies import AdminDaoDependencyMarker, EntityNotFound, \
    AdminDaoProto
from fastapi_admin2.providers.security.dto import InitAdmin, RenewPasswordCredentials, LoginCredentials
from fastapi_admin2.providers.security.password_hashing.protocol import HashVerifyFailedError, \
    PasswordHasherProto
from fastapi_admin2.providers.security.responses import to_init_page, to_login_page
from fastapi_admin2.utils.depends import get_dependency_from_request_by_marker
from fastapi_admin2.utils.files import FileManager

if TYPE_CHECKING:
    from fastapi_admin2.app import FastAPIAdmin


def get_current_admin(request: Request) -> AbstractAdmin:
    admin = request.state.admin
    if not admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    return admin


SESSION_ID_KEY = "user_session:{session_id}"


class SecurityProvider(Provider):
    name = "security_provider"
    session_cookie_key = "user_session"

    def __init__(
            self,
            file_manager: FileManager,
            redis: Redis,
            password_hasher: PasswordHasherProto,
            login_path: str = "/login",
            logout_path: str = "/logout",
            login_page_template_name: str = "providers/login/login.html",
            login_logo_url: Optional[str] = None,
            login_title_translation_key: str = "login_title",
            keep_logined_in_seconds: int = 3600,
            keep_logined_with_checked_remember_me_in_seconds: int = 3600 * 24 * 7,
    ):
        self.login_path = login_path
        self.logout_path = logout_path
        self.template_name = login_page_template_name
        self.login_title_translation_key = login_title_translation_key
        self.login_logo_url = login_logo_url
        self._password_hasher = password_hasher
        self._file_manager = file_manager
        self._redis = redis
        self._keep_logined_with_checked_remember_me_in_seconds = keep_logined_with_checked_remember_me_in_seconds
        self._keep_logined_in_seconds = keep_logined_in_seconds

    def register(self, app: "FastAPIAdmin") -> None:
        super(SecurityProvider, self).register(app)

        app.get(self.login_path)(self.login_view)
        app.post(self.login_path)(self.login)
        app.get(self.logout_path)(self.logout)

        app.get("/init")(self.init_view)
        app.post("/init")(self.handle_creation_of_init_admin)

        app.get("/renew_password")(self.renew_password_view)
        app.post("/renew_password")(self.renew_password)

        app.add_middleware(BaseHTTPMiddleware, dispatch=self.authenticate_middleware)

    async def login_view(self, request: Request,
                         admin_dao: AdminDaoProto = Depends(AdminDaoDependencyMarker), ) -> Response:
        if not await admin_dao.is_exists_at_least_one_admin():
            return to_init_page(request)

        return await self.templates.create_html_response(
            self.template_name,
            context={
                "request": request,
                "login_logo_url": self.login_logo_url,
                "login_title": self.login_title_translation_key,
            },
        )

    async def login(
            self,
            request: Request,
            login_credentials: LoginCredentials = Depends(LoginCredentials.as_form),
            admin_dao: AdminDaoProto = Depends(AdminDaoDependencyMarker),
    ) -> Response:
        unauthorized_response = await self.templates.create_html_response(
            self.template_name,
            status_code=HTTP_401_UNAUTHORIZED,
            context={"request": request, "error": request.state.gettext("login_failed")},
        )
        try:
            admin = await admin_dao.get_one_admin_by_filters(username=login_credentials.username)
        except EntityNotFound:
            return unauthorized_response
        else:
            if self._is_password_hash_is_invalid(admin, login_credentials.password):
                return unauthorized_response

            if self._password_hasher.is_rehashing_required(admin.password):
                await admin_dao.update_admin({}, password=self._password_hasher.hash(admin.password))

        response = RedirectResponse(url=request.app.admin_path, status_code=HTTP_303_SEE_OTHER)
        if login_credentials.remember_me:
            expires_in_seconds = self._keep_logined_with_checked_remember_me_in_seconds
            response.set_cookie("remember_me", "on")
        else:
            expires_in_seconds = self._keep_logined_in_seconds
            response.delete_cookie("remember_me")

        session_id = uuid.uuid4().hex
        response.set_cookie(
            self.session_cookie_key,
            session_id,
            expires=expires_in_seconds,
            path=request.app.admin_path,
            httponly=True
        )
        await self._redis.set(SESSION_ID_KEY.format(session_id=session_id), admin.id, ex=expires_in_seconds)
        return response

    async def logout(self, request: Request) -> Response:
        response = to_login_page(request)
        response.delete_cookie(self.session_cookie_key, path=request.app.admin_path)
        session_id = request.cookies[self.session_cookie_key]
        await self._redis.delete(SESSION_ID_KEY.format(session_id=session_id))
        return response

    async def authenticate_middleware(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.admin = None

        paths_related_to_authentication_stuff = [self.login_path, "/init", "/renew_password"]

        if not (session_id := request.cookies.get(self.session_cookie_key)):
            if request.scope["path"] not in paths_related_to_authentication_stuff:
                return to_login_page(request)

        admin_id = await self._redis.get(SESSION_ID_KEY.format(session_id=session_id))
        admin_dao: AdminDaoProto = get_dependency_from_request_by_marker(request, AdminDaoDependencyMarker)
        try:
            admin = await admin_dao.get_one_admin_by_filters(id=int(admin_id))
        except (EntityNotFound, TypeError):
            return await call_next(request)

        request.state.admin = admin
        return await call_next(request)

    async def init_view(
            self,
            request: Request,
            admin_dao: AdminDaoProto = Depends(AdminDaoDependencyMarker)
    ) -> Response:
        if await admin_dao.is_exists_at_least_one_admin():
            return to_login_page(request)

        return await self.templates.create_html_response("init.html", context={"request": request})

    async def handle_creation_of_init_admin(
            self,
            request: Request,
            init_admin: InitAdmin = Depends(InitAdmin.as_form),
            admin_dao: AdminDaoProto = Depends(
                AdminDaoDependencyMarker
            )
    ):
        if await admin_dao.is_exists_at_least_one_admin():
            return to_login_page(request)

        if init_admin.password != init_admin.confirm_password:
            return await self.templates.create_html_response(
                "init.html",
                context={"request": request, "error": request.state.gettext("confirm_password_different")},
            )

        path_to_profile_pic = await self._file_manager.download_file(init_admin.profile_pic)

        await admin_dao.add_admin(
            username=init_admin.username,
            password=self._password_hasher.hash(init_admin.password),
            profile_pic=str(path_to_profile_pic)
        )

        return RedirectResponse(url=request.app.admin_path, status_code=HTTP_303_SEE_OTHER)

    async def renew_password_view(
            self,
            request: Request,
            resources=Depends(get_resources)
    ) -> Response:
        return await self.templates.create_html_response(
            "providers/login/renew_password.html",
            context={
                "request": request,
                "resources": resources,
            },
        )

    async def renew_password(
            self,
            request: Request,
            form: RenewPasswordCredentials = Depends(RenewPasswordCredentials.as_form),
            admin: AbstractAdmin = Depends(get_current_admin),
            resources: List[dict] = Depends(get_resources),
            admin_dao: AdminDaoProto = Depends(AdminDaoDependencyMarker)
    ) -> Response:
        error = None
        if self._is_password_hash_is_invalid(admin, form.old_password):
            error = request.state.gettext("old_password_error")

        if form.new_password != form.confirmation_new_password:
            error = request.state.gettext("new_password_different")

        if error:
            return await self.templates.create_html_response(
                "renew_password.html",
                context={"request": request, "resources": resources, "error": error},
            )

        await admin_dao.update_admin({"id": admin.id}, password=form.new_password)
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
