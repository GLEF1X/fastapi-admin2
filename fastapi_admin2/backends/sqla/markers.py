from typing import Union, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from fastapi_admin2.utils.depends import DependencyMarker


class AsyncSessionDependencyMarker(DependencyMarker[Union[AsyncIterator[AsyncSession], AsyncSession]]):
    pass


class SessionMakerDependencyMarker(DependencyMarker[sessionmaker]):
    pass
