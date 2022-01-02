from typing import Dict, List, Optional, Type, Any

from aioredis import Redis
from fastapi import FastAPI
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, \
    HTTP_500_INTERNAL_SERVER_ERROR

from fastapi_admin.i18n.middleware import AbstractI18nMiddleware
from fastapi_admin.i18n.stub import _I18nMiddlewareStub
from fastapi_admin.providers import Provider
from . import template
from .database.models.abstract_admin import AbstractAdmin
from .database.repository.admin import AdminRepository
from .exceptions import not_found_error_exception, server_error_exception, forbidden_error_exception, \
    unauthorized_error_exception
from .general_dependencies import AsyncSessionDependencyMarker, SessionMakerDependencyMarker
from .providers.security.dependencies import UserRepositoryDependencyMarker, RedisClientDependencyMarker
from .resources import Dropdown
from .resources import Model as ModelResource
from .resources.base import Resource
from .routes import resources


class FastAPIAdmin(FastAPI):
    logo_url: str
    login_logo_url: str
    admin_path: str
    resources: List[Type[Resource]] = []
    model_resources: Dict[Type[Any], Type[Resource]] = {}
    redis: Redis
    language_switch: bool = True
    favicon_url: Optional[HttpUrl] = None

    def configure(
            self,
            logo_url: Optional[str] = None,
            admin_path: str = "/admin",
            template_folders: Optional[List[str]] = None,
            providers: Optional[List[Provider]] = None,
            favicon_url: Optional[HttpUrl] = None,
            i18n_middleware: Type[AbstractI18nMiddleware] = _I18nMiddlewareStub
    ):
        self.admin_path = admin_path
        self.logo_url = logo_url
        self.favicon_url = favicon_url
        if template_folders:
            template.add_template_folder(*template_folders)
        self._register_providers(providers)

        self.add_middleware(i18n_middleware)

        if issubclass(i18n_middleware, _I18nMiddlewareStub):
            self.language_switch = False

    def _register_providers(self, providers: Optional[List[Provider]] = None):
        for p in providers or []:
            p.register(self)

    def register_resources(self, *resource: Type[Resource]) -> None:
        for r in resource:
            self.register(r)

    def register(self, resource: Type[Resource]) -> None:
        self._set_model_resource(resource)
        self.resources.append(resource)

    def _set_model_resource(self, resource: Type[Resource]):
        if issubclass(resource, ModelResource):
            self.model_resources[resource.model] = resource
        elif issubclass(resource, Dropdown):
            for r in resource.resources:
                self._set_model_resource(r)

    def get_model_resource(self, model: Type[Any]):
        r = self.model_resources.get(model)
        return r() if r else None


def setup_admin_application(
        engine: AsyncEngine,
        session_maker: sessionmaker,
        redis: Redis,
        add_custom_exception_handlers: bool = True,
        admin_model_cls: Type[AbstractAdmin] = AbstractAdmin
) -> FastAPIAdmin:
    app = FastAPIAdmin()

    app.dependency_overrides[UserRepositoryDependencyMarker] = lambda: AdminRepository(
        session_maker(), admin_model_cls
    )
    app.dependency_overrides[RedisClientDependencyMarker] = lambda: redis

    async def spin_up_session():
        session: AsyncSession = session_maker()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[AsyncSessionDependencyMarker] = spin_up_session
    app.dependency_overrides[SessionMakerDependencyMarker] = lambda: session_maker

    @app.on_event("shutdown")
    async def on_shutdown():
        await engine.dispose()

    if add_custom_exception_handlers:
        app.add_exception_handler(HTTP_500_INTERNAL_SERVER_ERROR, server_error_exception)
        app.add_exception_handler(HTTP_404_NOT_FOUND, not_found_error_exception)
        app.add_exception_handler(HTTP_403_FORBIDDEN, forbidden_error_exception)
        app.add_exception_handler(HTTP_401_UNAUTHORIZED, unauthorized_error_exception)

    app.include_router(resources.router)

    return app
