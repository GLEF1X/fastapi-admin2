from typing import Protocol, Any, Dict, Type

from sqlalchemy import select, exists, insert, update
from sqlalchemy.exc import MultipleResultsFound, SQLAlchemyError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_admin.database.models.abstract import Admin


class AdministratorNotFound(Exception):
    def __init__(self, origin_exception: SQLAlchemyError):
        self.origin_exception = origin_exception


class UserRepositoryProto(Protocol):

    async def get_one_admin_by_filters(self, **filters: Any) -> Admin: ...

    async def is_exists_at_least_one_admin(self, **filters: Any) -> bool: ...

    async def add_user(self, **values: Any) -> None: ...

    async def update_admin(self, filters: Dict[Any, Any], **values: Any) -> None: ...


class UserRepository:

    def __init__(self, session: AsyncSession, admin_model_cls: Type[Admin]):
        self._session = session
        self._admin_model_cls = admin_model_cls

    async def get_one_admin_by_filters(self, **filters: Any) -> Admin:
        async with self._session.begin():
            stmt = select(self._admin_model_cls).filter_by(**filters)
            try:
                return (await self._session.execute(stmt)).scalars().one()
            except (MultipleResultsFound, NoResultFound) as ex:
                raise AdministratorNotFound(ex)

    async def is_exists_at_least_one_admin(self, **filters: Any) -> bool:
        async with self._session.begin():
            stmt = exists(self._admin_model_cls).select().filter_by(**filters).limit(1)
            return (await self._session.execute(stmt)).scalar()

    async def add_user(self, **values: Any) -> None:
        async with self._session.begin():
            stmt = insert(self._admin_model_cls).values(**values)
            return await self._session.execute(stmt)

    async def update_admin(self, filters: Dict[Any, Any], **values: Any) -> None:
        async with self._session.begin():
            stmt = update(self._admin_model_cls).filter_by(**filters).values(**values)
            await self._session.execute(stmt)
