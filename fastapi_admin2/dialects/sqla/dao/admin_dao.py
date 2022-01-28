from typing import Type, Any, Dict

from sqlalchemy import select, exists, insert, update
from sqlalchemy.exc import MultipleResultsFound, NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_admin2.base.entities import AbstractAdmin
from fastapi_admin2.dialects.sqla.models import SqlalchemyAdminModel
from fastapi_admin2.providers.security.dependencies import EntityNotFound


class SqlalchemyAdminDao:

    def __init__(self, session: AsyncSession, admin_model_cls: Type[SqlalchemyAdminModel]):
        self._session = session
        self._admin_model_cls = admin_model_cls

    async def get_one_admin_by_filters(self, **filters: Any) -> AbstractAdmin:
        stmt = select(self._admin_model_cls).filter_by(**filters)
        async with self._session.begin():
            try:
                return (await self._session.execute(stmt)).scalars().one()
            except (MultipleResultsFound, NoResultFound) as ex:
                raise AdministratorNotFound(ex)

    async def is_exists_at_least_one_admin(self, **filters: Any) -> bool:
        stmt = exists(self._admin_model_cls).select().filter_by(**filters).limit(1)
        async with self._session.begin():
            return (await self._session.execute(stmt)).scalar()

    async def add_admin(self, **values: Any) -> None:
        stmt = insert(self._admin_model_cls).values(**values)
        async with self._session.begin():
            return await self._session.execute(stmt)

    async def update_admin(self, filters: Dict[Any, Any], **values: Any) -> None:
        stmt = update(self._admin_model_cls).filter_by(**filters).values(**values)
        async with self._session.begin():
            await self._session.execute(stmt)


class AdministratorNotFound(EntityNotFound):
    def __init__(self, origin_exception: SQLAlchemyError):
        self.origin_exception = origin_exception
