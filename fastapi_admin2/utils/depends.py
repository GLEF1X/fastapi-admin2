from __future__ import annotations

from typing import Generic, TypeVar, Type, TYPE_CHECKING

from starlette.requests import Request
from starlette.routing import Mount

if TYPE_CHECKING:
    from fastapi_admin2.app import FastAPIAdmin

T = TypeVar("T")


class DependencyResolvingError(Exception):
    pass


class DependencyMarker(Generic[T]):
    pass


def get_dependency_from_request_by_marker(request: Request, marker: Type[DependencyMarker[T]]) -> T:
    fastapi_admin_instance = get_fastapi_admin_instance_from_request(request)
    return fastapi_admin_instance.dependency_overrides[marker]()


def get_fastapi_admin_instance_from_request(request: Request) -> FastAPIAdmin:
    from fastapi_admin2.app import FastAPIAdmin

    if isinstance(request.app, FastAPIAdmin):
        return request.app

    if not isinstance(request.app, FastAPIAdmin):
        for route in request.app.router.routes:
            if not isinstance(route, Mount):
                continue
            if not isinstance(route.app, FastAPIAdmin):
                continue
            return route.app

    raise DependencyResolvingError("FastAPI admin instance not found in request")
