from typing import Type, Any, Dict, cast

from sqlalchemy import select, exists, insert, update
from sqlalchemy.exc import MultipleResultsFound, NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_admin2.backends.sqla.models import SqlalchemyAdminModel
from fastapi_admin2.entities import AbstractAdmin
from fastapi_admin2.providers.security.dependencies import EntityNotFound, AdminDaoProto


class SqlalchemyAdminDao(AdminDaoProto):

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
        select_statement = select(self._admin_model_cls.id).select_from(self._admin_model_cls).limit(1)
        if filters:
            select_statement = select_statement.filter_by(**filters)
        stmt = exists(select_statement).select()
        async with self._session.begin():
            return cast(bool, (await self._session.execute(stmt)).scalar())

    async def add_admin(self, **values: Any) -> None:
        stmt = insert(self._admin_model_cls).values(**values)
        async with self._session.begin():
            await self._session.execute(stmt)

    async def update_admin(self, filters: Dict[Any, Any], **values: Any) -> None:
        stmt = update(self._admin_model_cls).filter_by(**filters).values(**values)
        async with self._session.begin():
            await self._session.execute(stmt)


class AdministratorNotFound(EntityNotFound):
    def __init__(self, origin_exception: SQLAlchemyError):
        self.origin_exception = origin_exception
