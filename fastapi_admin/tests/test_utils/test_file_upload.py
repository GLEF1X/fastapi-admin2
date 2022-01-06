import io

import py.path
import pytest
from fastapi import UploadFile

from fastapi_admin.exceptions import FileExtNotAllowed
from fastapi_admin.utils.file_upload import OnPremiseFileUploader, StaticFileUploader

pytestmark = pytest.mark.asyncio


class TestOnPremiseFileUploader:
    async def test_upload(self, tmpdir: py.path.local):
        uploader = OnPremiseFileUploader(uploads_dir=tmpdir)
        upload_file = UploadFile(filename="test.txt", file=io.BytesIO(b"test"))

        await uploader.upload(upload_file)

        assert (tmpdir / "test.txt").isfile()
        assert str((tmpdir / "test.txt").read()) == "test"

    async def test_upload_with_allowed_file_extensions(self, tmpdir: py.path.local):
        uploader = OnPremiseFileUploader(uploads_dir=tmpdir, allow_extensions=["jpeg"])
        upload_file = UploadFile(filename="test.jpeg", file=io.BytesIO(b"test"))

        await uploader.upload(upload_file)

        assert (tmpdir / "test.jpeg").isfile()
        assert str((tmpdir / "test.jpeg").read()) == "test"

    async def test_fail_if_file_extension_not_allowed(self, tmpdir: py.path.local):
        uploader = OnPremiseFileUploader(uploads_dir=tmpdir, allow_extensions=["jpeg"])
        upload_file = UploadFile(filename="test.txt", file=io.BytesIO(b"test"))

        with pytest.raises(FileExtNotAllowed):
            await uploader.upload(upload_file)

    async def test_save_file(self, tmpdir: py.path.local):
        uploader = OnPremiseFileUploader(uploads_dir=tmpdir)

        await uploader.save_file("test.txt", b"test")

        assert (tmpdir / "test.txt").isfile()
        assert str((tmpdir / "test.txt").read()) == "test"


class TestStaticFileUploader:
    async def test_upload(self, tmpdir: py.path.local):
        uploader = StaticFileUploader(OnPremiseFileUploader(uploads_dir=tmpdir, allow_extensions=["jpeg"]),
                                      static_path_prefix="/static/uploads")
        upload_file = UploadFile(filename="test.jpeg", file=io.BytesIO(b"test"))

        path_to_file = await uploader.upload(upload_file)

        assert str(path_to_file) == "/static/uploads/test.jpeg"
