import os
from typing import Union

from starlette.datastructures import UploadFile

from fastapi_admin2.utils.files.base import FileManager, Link


class StaticFilesManager(FileManager):

    def __init__(self, file_uploader: FileManager, static_path_prefix: str = "/static/uploads"):
        self._file_uploader = file_uploader
        self._static_path_prefix = static_path_prefix

    async def download_file(self, file: UploadFile) -> Union[Link, os.PathLike]:
        await self._file_uploader.download_file(file)
        return Link(os.path.join(self._static_path_prefix, file.filename))