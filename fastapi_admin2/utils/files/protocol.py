import os
from typing import NewType, Protocol, Union

from starlette.datastructures import UploadFile

Link = NewType("Link", str)


class FileManager(Protocol):

    async def download_file(self, file: UploadFile) -> Union[Link, os.PathLike]: ...