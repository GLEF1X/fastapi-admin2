from typing import AsyncIterator, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from fastapi_admin.utils.depends import Marker


class AsyncSessionDependencyMarker(Marker[Union[AsyncIterator[AsyncSession], AsyncSession]]):
    pass


class SessionMakerDependencyMarker(Marker[sessionmaker]):
    pass
