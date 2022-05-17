import abc
import os
from typing import Optional, Union, Any

import anyio.to_thread
from aioboto3 import Session
from aiobotocore.client import AioBaseClient
from fastapi import UploadFile
from minio import Minio

from fastapi_admin2.utils.files import FileManager
from fastapi_admin2.utils.files.base import Link
from fastapi_admin2.utils.files.utils import create_unique_file_identifier


class S3Client(abc.ABC):

    def __init__(self, bucket_name: str, access_key: str, secret_key: str, region: str,
                 file_identifier_prefix: str):
        self._bucket_name = bucket_name
        self._access_key = access_key
        self._secret_key = secret_key
        self._region_name = region
        self._file_identifier_prefix = file_identifier_prefix

    @abc.abstractmethod
    async def create_bucket(self, bucket_name: str, **options: Any) -> None:
        pass

    @abc.abstractmethod
    async def delete_bucket(self, bucket_name: str) -> None:
        pass

    @abc.abstractmethod
    async def upload_file(self, file: UploadFile) -> str:
        pass


class AWSS3Client(S3Client):

    def __init__(self, bucket_name: str, access_key: str, secret_key: str, region: str,
                 file_identifier_prefix: str):
        super().__init__(bucket_name, access_key, secret_key, region, file_identifier_prefix)
        self._client: Optional[AioBaseClient] = None

    async def create_bucket(self, bucket_name: str, **options: Any) -> None:
        try:
            region = options.pop("region")
            options["CreateBucketConfiguration"] = {"LocationConstraint": region}
        except KeyError:
            pass

        async with self._get_client() as c:
            await c.create_bucket(Bucket=bucket_name, **options)

    async def delete_bucket(self, bucket_name: str) -> None:
        async with self._get_client() as c:
            await c.resource("s3").Bucket(bucket_name).objects.all().delete()

    async def upload_file(self, file: UploadFile) -> str:
        fi = create_unique_file_identifier(
            file, self._file_identifier_prefix
        )
        async with self._get_client() as c:
            await c.upload_fileobj(file, self._bucket_name, fi)

        return Link("https://{0}.s3.{1}.amazonaws.com/{2}".format(
            self._bucket_name, self._region_name, fi
        ))

    def _get_client(self) -> AioBaseClient:
        if self._client is None:
            session = Session(
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region_name
            )
            self._client = session.client("s3")

        return self._client


class MinioS3Client(S3Client):

    def __init__(
            self,
            bucket_name: str,
            access_key: str,
            secret_key: str,
            region: str,
            file_identifier_prefix: str,
            endpoint: str,
            session_token: Optional[str] = None,
            secure: bool = True,
            http_client=None,
            credentials=None
    ):
        super().__init__(bucket_name, access_key, secret_key, region, file_identifier_prefix)

        self._minio = Minio(
            endpoint, access_key, secret_key, session_token, secure, region, http_client, credentials
        )

    async def create_bucket(self, bucket_name: str, **options: Any) -> None:
        pass

    async def delete_bucket(self, bucket_name: str) -> None:
        pass

    async def upload_file(self, file: UploadFile) -> str:
        def sync_upload() -> str:
            fi = create_unique_file_identifier(file, self._file_identifier_prefix)
            obj = self._minio.put_object(
                bucket_name=self._bucket_name,
                object_name=fi,
                data=file.file,
                length=-1,
                part_size=10 * 1024 * 1024,
            )
            return self._minio.get_presigned_url(
                "PUT", bucket_name=self._bucket_name,
                object_name=fi,
                version_id=obj.version_id,
            )

        return await anyio.to_thread.run_sync(sync_upload)


class S3FileManager(FileManager):
    def __init__(self, s3_client: S3Client):
        self._s3_client = s3_client

    async def upload_file(self, file: UploadFile) -> Union[Link, os.PathLike]:
        return Link(await self._s3_client.upload_file(file))
