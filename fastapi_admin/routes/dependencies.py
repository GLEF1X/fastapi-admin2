from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_admin.utils.depends import Marker


class AsyncSessionDependencyMarker(Marker[AsyncSession]):
    pass
