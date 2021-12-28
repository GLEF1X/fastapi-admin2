from typing import Dict, List, Optional, Type, Any

from aioredis import Redis
from fastapi import FastAPI
from pydantic import HttpUrl
from tortoise import Model

from fastapi_admin.providers import Provider
from . import template
from .resources import Dropdown
from .resources import Model as ModelResource
from .resources import Resource
from .services.i18n.middleware import I18nMiddleware
from .services.i18n.stub import _I18nMiddlewareStub


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
            i18n_middleware: Type[I18nMiddleware] = _I18nMiddlewareStub
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

    def register_resources(self, *resource: Type[Resource]):
        for r in resource:
            self.register(r)

    def register(self, resource: Type[Resource]):
        self._set_model_resource(resource)
        self.resources.append(resource)

    def _set_model_resource(self, resource: Type[Resource]):
        if issubclass(resource, ModelResource):
            self.model_resources[resource.model] = resource
        elif issubclass(resource, Dropdown):
            for r in resource.resources:
                self._set_model_resource(r)

    def get_model_resource(self, model: Type[Model]):
        r = self.model_resources.get(model)
        return r() if r else None
