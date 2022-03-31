import os
import pathlib
from typing import Callable, Optional, Protocol, Sequence, Union, NewType

import aiofiles
from starlette.datastructures import UploadFile

from fastapi_admin2.exceptions import FileExtNotAllowed, FileMaxSizeLimit

DEFAULT_MAX_FILE_SIZE = 1024 ** 3

Link = NewType("Link", str)


class FileManager(Protocol):

    async def upload(self, file: UploadFile) -> Union[Link, os.PathLike]: ...


class OnPremiseFileManager:
    def __init__(
            self,
            uploads_dir: os.PathLike,
            allow_extensions: Optional[Sequence[str]] = None,
            max_size: int = DEFAULT_MAX_FILE_SIZE,
            filename_generator: Optional[Callable[[UploadFile], str]] = None
    ):
        self._max_size = max_size
        self._allow_extensions = allow_extensions
        self._uploads_dir = pathlib.Path(uploads_dir)
        self._filename_generator = filename_generator

    async def upload(self, file: UploadFile) -> Union[Link, os.PathLike]:
        if self._filename_generator:
            filename = self._filename_generator(file)
        else:
            filename = file.filename
        content = await file.read()
        file_size = len(content)
        if file_size > self._max_size:
            raise FileMaxSizeLimit(f"File size {file_size} exceeds max size {self._max_size}")

        if self._file_extension_is_not_allowed(filename):
            raise FileExtNotAllowed(f"File ext is not allowed of {self._allow_extensions}")

        return await self._save_file(filename, content)  # type: ignore

    async def _save_file(self, filename: str, content: bytes) -> os.PathLike:
        """
        Save file to upload directory / filename

        :param filename:
        :param content:
        :return: relative path to upload directory
        """
        path_to_file = self._uploads_dir / filename
        async with aiofiles.open(path_to_file, "wb") as f:
            await f.write(content)
        return path_to_file

    def _file_extension_is_not_allowed(self, filename: str) -> bool:
        if not self._allow_extensions:
            return False
        return all(not filename.endswith(ext) for ext in self._allow_extensions)


class StaticFilesManager:

    def __init__(self, file_uploader: FileManager, static_path_prefix: str = "/static/uploads"):
        self._file_uploader = file_uploader
        self._static_path_prefix = static_path_prefix

    async def upload(self, file: UploadFile) -> Union[Link, os.PathLike]:
        await self._file_uploader.upload(file)
        return Link(os.path.join(self._static_path_prefix, file.filename))
