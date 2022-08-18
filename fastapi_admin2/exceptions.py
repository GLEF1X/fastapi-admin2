from typing import Optional

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


class ServerHTTPException(HTTPException):
    def __init__(self, error: str = None):
        super(ServerHTTPException, self).__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )


class InvalidResource(ServerHTTPException):
    """
    raise when has invalid resource
    """


class FieldNotFoundError(ServerHTTPException):
    """
    raise when no such field for the given
    """


class FileMaxSizeLimit(ServerHTTPException):
    """
    raise when the upload file exceeds the max size
    """


class FileExtNotAllowed(ServerHTTPException):
    """
    raise when the upload file ext not allowed
    """


class DatabaseError(Exception):
    """
    raise when the repository go wrong
    """


class RequiredThirdPartyLibNotInstalled(Exception):
    def __init__(self, lib_name: str, *, thing_that_cant_work_without_lib: str,
                 can_be_installed_with_ext: Optional[str] = None):
        self.thing_that_cant_work_without_lib = thing_that_cant_work_without_lib
        self.can_be_installed_with_ext = can_be_installed_with_ext
        self.lib_name = lib_name

        if not self.can_be_installed_with_ext:
            self.can_be_installed_with_ext = ""
        else:
            self.can_be_installed_with_ext = f"[{can_be_installed_with_ext}]"

        super().__init__(
            f"{self.thing_that_cant_work_without_lib} can be used only when {self.lib_name} installed\n"
            f"Just install {self.lib_name} (`pip install {self.lib_name}`) "
            f"or fastapi-admin2 with {self.thing_that_cant_work_without_lib} support"
            f" (`pip install fastapi-admin2{self.can_be_installed_with_ext}`)"
        )
