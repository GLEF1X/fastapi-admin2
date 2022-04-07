from typing import Any, Dict, Type

from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from fastapi_admin2.backends.tortoise.dao.admin_dao import TortoiseAdminDao
from fastapi_admin2.backends.tortoise.models import AbstractAdminModel
from fastapi_admin2.backends.tortoise.models import Model
from fastapi_admin2.backends.tortoise.queriers import get_resource_list, delete_one_by_id, \
    bulk_delete_resources
from fastapi_admin2.providers.security.dependencies import AdminDaoDependencyMarker
from fastapi_admin2.controllers.dependencies import ModelListDependencyMarker, DeleteOneDependencyMarker, \
    DeleteManyDependencyMarker


class TortoiseBackend:

    def __init__(self, registration_config: Dict[str, Any], admin_model_cls: Type[AbstractAdminModel]):
        self._admin_model_cls = admin_model_cls
        self._config = registration_config

    def configure(self, app: FastAPI) -> None:
        register_tortoise(app, **self._config)

        app.dependency_overrides[AdminDaoDependencyMarker] = lambda: TortoiseAdminDao(self._admin_model_cls)

        app.dependency_overrides[ModelListDependencyMarker] = get_resource_list
        app.dependency_overrides[DeleteOneDependencyMarker] = delete_one_by_id
        app.dependency_overrides[DeleteManyDependencyMarker] = bulk_delete_resources


__all__ = ('TortoiseBackend', 'Model')
