import os
import pathlib
from typing import Callable, List, Optional, Protocol, NewType

import aiofiles
from starlette.datastructures import UploadFile

from fastapi_admin.exceptions import FileExtNotAllowed, FileMaxSizeLimit

FileLocation = NewType("FileLocation", str)


class FileUploader(Protocol):

    async def save_file(self, filename: str, content: bytes) -> FileLocation: ...

    async def upload(self, file: UploadFile) -> FileLocation: ...


class DiskFileUploader:
    def __init__(
            self,
            uploads_dir: os.PathLike,
            allow_extensions: Optional[List[str]] = None,
            max_size: int = 1024 ** 3,
            filename_generator: Optional[Callable[[UploadFile], str]] = None,
            prefix: str = "/static/uploads",
    ):
        self.max_size = max_size
        self.allow_extensions = allow_extensions
        self.uploads_dir = pathlib.Path(uploads_dir)
        self.filename_generator = filename_generator
        self.prefix = prefix

    async def save_file(self, filename: str, content: bytes) -> FileLocation:
        path_to_file = self.uploads_dir / filename
        async with aiofiles.open(path_to_file, "wb") as f:
            await f.write(content)
        return FileLocation(os.path.join(self.prefix, filename))

    async def upload(self, file: UploadFile) -> FileLocation:
        if self.filename_generator:
            filename = self.filename_generator(file)
        else:
            filename = file.filename
        content = await file.read()
        file_size = len(content)
        if file_size > self.max_size:
            raise FileMaxSizeLimit(f"File size {file_size} exceeds max size {self.max_size}")

        if self._file_has_not_allowed_extension(filename):
            raise FileExtNotAllowed(f"File ext is not allowed of {self.allow_extensions}")

        return FileLocation(await self.save_file(filename, content))

    def _file_has_not_allowed_extension(self, filename: str) -> bool:
        if not self.allow_extensions:
            return False
        for ext in self.allow_extensions:
            if filename.endswith(ext):
                return True
        return False
