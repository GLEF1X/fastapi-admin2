import os
import pathlib
from typing import Callable, Optional, Protocol, NewType, Sequence

import aiofiles
from starlette.datastructures import UploadFile

from fastapi_admin.exceptions import FileExtNotAllowed, FileMaxSizeLimit

FileLocation = NewType("FileLocation", str)


class FileUploader(Protocol):

    async def save_file(self, filename: str, content: bytes) -> os.PathLike: ...

    async def upload(self, file: UploadFile) -> FileLocation: ...


class DiskFileUploader:
    def __init__(
            self,
            uploads_dir: os.PathLike,
            allow_extensions: Optional[Sequence[str]] = None,
            max_size: int = 1024 ** 3,
            filename_generator: Optional[Callable[[UploadFile], str]] = None,
            prefix: str = "/static/uploads"
    ):
        self._max_size = max_size
        self._allow_extensions = allow_extensions
        self._uploads_dir = pathlib.Path(uploads_dir)
        self._filename_generator = filename_generator
        self._prefix = prefix

    async def upload(self, file: UploadFile) -> FileLocation:
        if self._filename_generator:
            filename = self._filename_generator(file)
        else:
            filename = file.filename
        content = await file.read()
        file_size = len(content)
        if file_size > self._max_size:
            raise FileMaxSizeLimit(f"File size {file_size} exceeds max size {self._max_size}")

        if self._file_has_not_allowed_extension(filename):
            raise FileExtNotAllowed(f"File ext is not allowed of {self._allow_extensions}")

        return FileLocation(str(await self.save_file(filename, content)))

    async def save_file(self, filename: str, content: bytes) -> os.PathLike:
        """
        Save file to upload directory / filename

        :param filename:
        :param content:
        :return: relative path to upload directory
        """
        path_to_file = self._uploads_dir / filename
        async with aiofiles.open(path_to_file, "wb") as f:
            await f.write(content)
        return pathlib.Path(self._prefix).joinpath(filename)

    def _file_has_not_allowed_extension(self, filename: str) -> bool:
        if not self._allow_extensions:
            return False
        for ext in self._allow_extensions:
            if filename.endswith(ext):
                return True
        return False
