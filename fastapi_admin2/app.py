import os
from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence, Type, Union
from typing import Protocol

from fastapi import FastAPI
from fastapi.datastructures import Default
from fastapi.params import Depends
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, \
    HTTP_500_INTERNAL_SERVER_ERROR


from fastapi_admin2.providers import Provider
from fastapi_admin2.utils.templating import JinjaTemplates
from .middlewares.i18n.base import AbstractI18nMiddleware
from .middlewares.i18n.impl import I18nMiddleware
from .middlewares.theme import theme_middleware
from .middlewares.templating import create_template_middleware
from .i18n.translator import I18nTranslator
from .resources import AbstractModelResource as ModelResource
from .resources import Dropdown
from .resources.base import Resource
from .responses import server_error_exception, not_found, forbidden, unauthorized
from .routes import resources


class ORMBackend(Protocol):
    def configure(self, app: FastAPI) -> None: ...


ORMModel = Any


class FastAPIAdmin(FastAPI):

    def __init__(
            self, *,
            orm_backend: ORMBackend,
            login_logo_url: Optional[str] = None,
            add_custom_exception_handlers: bool = True,
            logo_url: Optional[str] = None,
            admin_path: str = "/admin",
            providers: Optional[List[Provider]] = None,
            favicon_url: Optional[str] = None,
            i18n_middleware_class: Optional[Type[AbstractI18nMiddleware]] = None,
            debug: bool = False, routes: Optional[List[BaseRoute]] = None,
            title: str = "FastAPI",
            description: str = "",
            version: str = "0.1.0",
            openapi_url: Optional[str] = "/openapi.json",
            openapi_tags: Optional[List[Dict[str, Any]]] = None,
            servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
            dependencies: Optional[Sequence[Depends]] = None,
            default_response_class: Type[Response] = Default(JSONResponse),
            docs_url: Optional[str] = "/docs",
            redoc_url: Optional[str] = "/redoc",
            swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
            swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
            middleware: Optional[Sequence[Middleware]] = None,
            exception_handlers: Optional[Dict[
                Union[int, Type[Exception]],
                Callable[[Request, Any], Coroutine[Any, Any, Response]],
            ]] = None,
            on_startup: Optional[Sequence[Callable[[], Any]]] = None,
            on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
            terms_of_service: Optional[str] = None, contact: Optional[Dict[str, Union[str, Any]]] = None,
            license_info: Optional[Dict[str, Union[str, Any]]] = None,
            openapi_prefix: str = "",
            root_path: str = "", root_path_in_servers: bool = True,
            responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
            callbacks: Optional[List[BaseRoute]] = None, deprecated: Optional[bool] = None,
            include_in_schema: bool = True, **extra: Any
    ) -> None:
        super().__init__(
            debug=debug, routes=routes, title=title, description=description, version=version,
            openapi_url=openapi_url, openapi_tags=openapi_tags, servers=servers,
            dependencies=dependencies, default_response_class=default_response_class,
            docs_url=docs_url, redoc_url=redoc_url,
            swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
            swagger_ui_init_oauth=swagger_ui_init_oauth, middleware=middleware,
            exception_handlers=exception_handlers, on_startup=on_startup,
            on_shutdown=on_shutdown, terms_of_service=terms_of_service, contact=contact,
            license_info=license_info, openapi_prefix=openapi_prefix, root_path=root_path,
            root_path_in_servers=root_path_in_servers, responses=responses, callbacks=callbacks,
            deprecated=deprecated, include_in_schema=include_in_schema, **extra
        )

        self.admin_path = admin_path
        self.login_logo_url = login_logo_url
        self.admin_path = admin_path

        self.logo_url = logo_url
        self.favicon_url = favicon_url

        translator = I18nTranslator()

        self.templates = JinjaTemplates()
        self.templates.env.add_extension("jinja2.ext.i18n")
        self.middleware("http")(create_template_middleware(self.templates))
        self.dependency_overrides[JinjaTemplates] = lambda: self.templates

        if i18n_middleware_class is None:
            i18n_middleware_class = I18nMiddleware
        self.add_middleware(i18n_middleware_class, translator=translator)
        self.language_switch = True

        self.middleware('http')(theme_middleware)

        self._orm_backend = orm_backend
        self._orm_backend.configure(self)

        self.resources: List[Type[Resource]] = []
        self.model_resources: Dict[Type[ORMModel], Type[Resource]] = {}

        if add_custom_exception_handlers:
            exception_handlers = {
                HTTP_500_INTERNAL_SERVER_ERROR: server_error_exception,
                HTTP_404_NOT_FOUND: not_found,
                HTTP_403_FORBIDDEN: forbidden,
                HTTP_401_UNAUTHORIZED: unauthorized
            }
            for http_status, h in exception_handlers.items():
                self.add_exception_handler(http_status, h)

        for p in providers:
            self.register_provider(p)
        self.include_router(resources.router)

    def register_provider(self, provider: Provider) -> None:
        provider.register(self)

    def register_resource(self, resource: Type[Resource]) -> None:
        self._set_model_resource(resource)
        self.resources.append(resource)

    def _set_model_resource(self, resource: Type[Resource]) -> None:
        if issubclass(resource, ModelResource):
            self.model_resources[resource.model] = resource
        elif issubclass(resource, Dropdown):
            for r in resource.resources:
                self._set_model_resource(r)

    def get_model_resource_type(self, model: Type[ORMModel]) -> Optional[Type[Resource]]:
        return self.model_resources.get(model)

    def add_template_folder(self, folder: Union[str, os.PathLike]) -> None:
        self.templates.env.loader.searchpath.insert(0, folder)
