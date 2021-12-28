import dataclasses

from fastapi import Form, UploadFile, File


@dataclasses.dataclass(frozen=True)
class InitAdmin:
    username: str = Form(...)
    password: str = Form(...)
    confirm_password: str = Form(...)
    avatar: UploadFile = File(...)
