from pydantic import BaseModel

from fastapi import Form, UploadFile, File


class InitAdmin(BaseModel):
    username: str = Form(...)
    password: str = Form(...)
    confirm_password: str = Form(...)
    avatar: UploadFile = File(...)


class RenewPasswordForm(BaseModel):
    old_password: str = Form(...)
    new_password: str = Form(...)
    re_new_password: str = Form(...)
