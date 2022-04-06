from __future__ import annotations

from typing import Type

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from fastapi_admin2.backends.sqla.dao.admin_dao import SqlalchemyAdminDao
from fastapi_admin2.backends.sqla.markers import AsyncSessionDependencyMarker, SessionMakerDependencyMarker
from fastapi_admin2.backends.sqla.models import SqlalchemyAdminModel
from fastapi_admin2.backends.sqla.queriers import get_resource_list, delete_resource_by_id, \
    bulk_delete_resources
from fastapi_admin2.providers.security.dependencies import AdminDaoDependencyMarker
from fastapi_admin2.routes.dependencies import ModelListDependencyMarker, DeleteOneDependencyMarker, \
    DeleteManyDependencyMarker
from . import filters
from .model_resource import Model


class SQLAlchemyBackend:
    def __init__(self, session_maker: sessionmaker, admin_model_cls: Type[SqlalchemyAdminModel]):
        self._session_maker = session_maker
        self._admin_model_cls = admin_model_cls

    def configure(self, app: FastAPI) -> None:
        # It's not neccessary in all cases, but for some kind of authorization it can be useful
        app.dependency_overrides[AdminDaoDependencyMarker] = lambda: SqlalchemyAdminDao(
            self._session_maker(), self._admin_model_cls
        )

        async def spin_up_session():
            session: AsyncSession = self._session_maker()
            try:
                yield session
            finally:
                await session.close()

        app.dependency_overrides[AsyncSessionDependencyMarker] = spin_up_session
        app.dependency_overrides[SessionMakerDependencyMarker] = lambda: self._session_maker

        # route dependencies
        app.dependency_overrides[DeleteOneDependencyMarker] = delete_resource_by_id
        app.dependency_overrides[DeleteManyDependencyMarker] = bulk_delete_resources
        app.dependency_overrides[ModelListDependencyMarker] = get_resource_list
