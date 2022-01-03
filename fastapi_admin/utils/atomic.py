import asyncio
import functools
from typing import TypeVar, Callable, Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response

from fastapi_admin.general_dependencies import SessionMakerDependencyMarker
from fastapi_admin.utils.depends import get_dependency_from_request_by_marker

_F = TypeVar("_F", bound=Callable[..., Any])


class UnsupportedTypeOfHandler(Exception):
    pass


class AtomicSession:
    pass


def atomic(func: _F) -> _F:
    """
    Makes view atomic.
    Decorates a view and wraps it in a single transaction, so all executed statements within this view will be atomic

    >>> @atomic
    >>> async def some_view(request, session: AsyncSession = Depends(AtomicSession)):
    >>>     # the following executions will be executed within 1 transaction
    >>>     await session.execute(stmt1)
    >>>     await session.execute(stmt2)

    :return: atomic view
    """
    if not asyncio.iscoroutinefunction(func):
        raise UnsupportedTypeOfHandler("`atomic` decorator supports only async handlers/views")

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Response:
        request: Request = kwargs.get("request")
        session_pool = get_dependency_from_request_by_marker(request, SessionMakerDependencyMarker)
        async with session_pool.begin() as session:  # type: AsyncSession
            kwargs.update(session=session)
            return await func(*args, **kwargs)

    return async_wrapper
