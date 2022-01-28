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

from fastapi_admin2.i18n.middleware import AbstractI18nMiddleware
from fastapi_admin2.i18n.stub import _I18nMiddlewareStub
from fastapi_admin2.providers import Provider
from . import template
from .exceptions import not_found_error_exception, server_error_exception, forbidden_error_exception, \
    unauthorized_error_exception
from .resources import AbstractModelResource as ModelResource
from .resources import Dropdown
from .resources.base import Resource
from .routes import resources


class ORMDialect(Protocol):
    def configure(self, app: FastAPI) -> None: ...


class FastAPIAdmin(FastAPI):

    def __init__(self, *,
                 dialect: ORMDialect,
                 login_logo_url: Optional[str] = None,
                 add_custom_exception_handlers: bool = True,
                 logo_url: Optional[str] = None,
                 admin_path: str = "/admin",
                 template_folders: Optional[List[Union[os.PathLike, str]]] = None,
                 providers: Optional[List[Provider]] = None,
                 favicon_url: Optional[str] = None,
                 i18n_middleware: Type[AbstractI18nMiddleware] = _I18nMiddlewareStub,
                 debug: bool = False, routes: Optional[List[BaseRoute]] = None,
                 title: str = "FastAPI", description: str = "", version: str = "0.1.0",
                 openapi_url: Optional[str] = "/openapi.json",
                 openapi_tags: Optional[List[Dict[str, Any]]] = None,
                 servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
                 dependencies: Optional[Sequence[Depends]] = None,
                 default_response_class: Type[Response] = Default(JSONResponse),
                 docs_url: Optional[str] = "/docs", redoc_url: Optional[str] = "/redoc",
                 swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
                 swagger_ui_init_oauth: Optional[Dict[str, Any]] = None,
                 middleware: Optional[Sequence[Middleware]] = None, exception_handlers: Optional[
                Dict[
                    Union[int, Type[Exception]],
                    Callable[[Request, Any], Coroutine[Any, Any, Response]],
                ]
            ] = None, on_startup: Optional[Sequence[Callable[[], Any]]] = None,
                 on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
                 terms_of_service: Optional[str] = None, contact: Optional[Dict[str, Union[str, Any]]] = None,
                 license_info: Optional[Dict[str, Union[str, Any]]] = None, openapi_prefix: str = "",
                 root_path: str = "", root_path_in_servers: bool = True,
                 responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
                 callbacks: Optional[List[BaseRoute]] = None, deprecated: Optional[bool] = None,
                 include_in_schema: bool = True, **extra: Any) -> None:
        super().__init__(debug=debug, routes=routes, title=title, description=description, version=version,
                         openapi_url=openapi_url, openapi_tags=openapi_tags, servers=servers,
                         dependencies=dependencies, default_response_class=default_response_class,
                         docs_url=docs_url, redoc_url=redoc_url,
                         swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
                         swagger_ui_init_oauth=swagger_ui_init_oauth, middleware=middleware,
                         exception_handlers=exception_handlers, on_startup=on_startup,
                         on_shutdown=on_shutdown, terms_of_service=terms_of_service, contact=contact,
                         license_info=license_info, openapi_prefix=openapi_prefix, root_path=root_path,
                         root_path_in_servers=root_path_in_servers, responses=responses, callbacks=callbacks,
                         deprecated=deprecated, include_in_schema=include_in_schema, **extra)

        self.admin_path = admin_path
        self.login_logo_url = login_logo_url

        self.admin_path = admin_path
        self.logo_url = logo_url
        self.favicon_url = favicon_url
        if template_folders:
            template.add_template_folder(*template_folders)

        self.add_middleware(i18n_middleware)
        self.language_switch = True

        self._dialect = dialect

        self.resources: List[Type[Resource]] = []
        self.model_resources: Dict[Type[Any], Type[Resource]] = {}
        self.favicon_url: Optional[str] = None

        if add_custom_exception_handlers:
            self.add_exception_handler(HTTP_500_INTERNAL_SERVER_ERROR, server_error_exception)
            self.add_exception_handler(HTTP_404_NOT_FOUND, not_found_error_exception)
            self.add_exception_handler(HTTP_403_FORBIDDEN, forbidden_error_exception)
            self.add_exception_handler(HTTP_401_UNAUTHORIZED, unauthorized_error_exception)

        if issubclass(i18n_middleware, _I18nMiddlewareStub):
            self.language_switch = False

        self._register_providers(providers)
        self.include_router(resources.router)
        self._dialect.configure(self)

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

    def get_model_resource(self, model: Type[Any]) -> Optional[Resource]:
        r = self.model_resources.get(model)
        return r() if r else None
