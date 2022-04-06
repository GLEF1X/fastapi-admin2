import os
from typing import Optional, Union

from aioboto3 import Session
from aiobotocore.client import AioBaseClient
from fastapi import UploadFile

from fastapi_admin2.utils.files import FileManager
from fastapi_admin2.utils.files.base import Link
from fastapi_admin2.utils.files.utils import create_unique_file_identifier


class S3FileManager(FileManager):
    def __init__(self, bucket_name: str, access_key: str, secret_key: str, region: str,
                 file_identifier_prefix: str) -> None:
        self._client: Optional[AioBaseClient] = None
        self._bucket_name = bucket_name
        self._access_key = access_key
        self._secret_key = secret_key
        self._region_name = region
        self._file_identifier_prefix = file_identifier_prefix

    async def download_file(self, file: UploadFile) -> Union[Link, os.PathLike]:
        file_identifier = create_unique_file_identifier(file, self._file_identifier_prefix)

        async with await self.connect() as s3:  # type: AioBaseClient
            await s3.upload_fileobj(file.file, self._bucket_name, file_identifier)

        return Link("https://{0}.s3.{1}.amazonaws.com/{2}".format(
            self._bucket_name, self._region_name, file_identifier
        ))

    async def connect(self) -> AioBaseClient:
        if self._client is None:
            session = Session(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region_name
            )
            self._client = session.client("s3")

        return self._client
