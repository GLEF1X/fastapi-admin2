from typing import Generic, TypeVar, Type

from starlette.requests import Request

T = TypeVar("T")


class Marker(Generic[T]):
    pass


def get_dependency_from_request_by_marker(request: Request, marker: Type[Marker[T]]) -> T:
    return request.app.dependency_overrides[marker]()
