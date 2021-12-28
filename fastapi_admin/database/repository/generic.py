from abc import ABC
from typing import TypeVar, Generic, Union, cast, Any, Dict, List, Optional

from sqlalchemy import lambda_stmt, select, func, exists, update, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import Executable

T = TypeVar("T")


class GenericRepository(ABC, Generic[T]):

    def __init__(self, session_or_pool: Union[sessionmaker, AsyncSession], model: T) -> None:
        if isinstance(session_or_pool, sessionmaker):
            self._session: AsyncSession = cast(AsyncSession, session_or_pool())
        else:
            self._session = session_or_pool
        self.model = model

    @staticmethod
    def proxy_bulk_save(session: Session, *instances) -> None:
        return session.bulk_save_objects(*instances)

    async def insert(self, **values: Any) -> T:
        """Add model into database"""
        insert_stmt = (
            insert(self.model)
                .values(**values)
                .returning(self.model)
        )
        result = (await self._session.execute(insert_stmt)).mappings().first()
        return self._convert_to_model(cast(Dict[str, Any], result))

    async def select_all(self, **filters: Any) -> List[T]:
        """
        Selecting data from table and filter by kwargs data
        :param clauses:
        :return:
        """
        query_model = self.model
        stmt = lambda_stmt(lambda: select(query_model))
        stmt += lambda s: s.filter_by(**filters)
        result = (
            (await self._session.execute(cast(Executable, stmt)))
                .scalars()
                .all()
        )

        return result

    async def select_one(self, **filters: Any) -> T:
        """
        Return scalar value
        :return:
        """
        query_model = self.model
        stmt = lambda_stmt(lambda: select(query_model))
        stmt += lambda s: s.filter_by(**filters)
        result = (
            (await self._session.execute(cast(Executable, stmt)))
                .scalars()
                .first()
        )

        return cast(T, result)

    async def update(self, filters: Dict[Any, Any], **values: Any) -> None:
        """
        Update values in database, filter by `telegram_id`
        :param filters: where conditionals
        :param values: key/value for update
        :return:
        """
        stmt = update(self.model).filter_by(**filters).values(**values).returning(None)
        await self._session.execute(stmt)
        return None

    async def exists(self, **filters: Any) -> Optional[bool]:
        """Check is user exists in database"""
        stmt = exists(select(self.model).filter_by(**filters)).select()
        result = (await self._session.execute(stmt)).scalar()
        return cast(Optional[bool], result)

    async def delete(self, **filters: Any) -> List[T]:
        stmt = delete(self.model).filter_by(**filters).returning("*")
        result = (await self._session.execute(stmt)).mappings().all()
        return list(map(self._convert_to_model, result))

    async def count(self) -> int:
        count = (await self._session.execute(func.count("*"))).scalars().first()
        return cast(int, count)

    def _convert_to_model(self, kwargs) -> T:
        return self.model(**kwargs)  # type: ignore
