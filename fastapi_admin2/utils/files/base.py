import abc
import os
from typing import NewType, Union

from starlette.datastructures import UploadFile

Link = NewType("Link", str)


class FileManager(abc.ABC):

    @abc.abstractmethod
    async def download_file(self, file: UploadFile) -> Union[Link, os.PathLike]:
        pass
