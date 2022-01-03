import dataclasses

from fastapi import Form, UploadFile, File


@dataclasses.dataclass(frozen=True)
class InitAdmin:
    username: str = Form(...)
    password: str = Form(...)
    confirm_password: str = Form(...)
    avatar: UploadFile = File(...)


@dataclasses.dataclass(frozen=True)
class RenewPasswordForm:
    old_password: str = Form(...)
    new_password: str = Form(...)
    re_new_password: str = Form(...)
