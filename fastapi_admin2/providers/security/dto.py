from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel, validator

from fastapi_admin2.utils.forms import as_form


@as_form
class InitAdmin(BaseModel):
    username: str
    password: str
    confirm_password: str
    profile_pic: UploadFile


@as_form
class RenewPasswordCredentials(BaseModel):
    old_password: str
    new_password: str
    confirmation_new_password: str


@as_form
class LoginCredentials(BaseModel):
    username: str
    password: str
    remember_me: bool

    @validator("remember_me", pre=True)
    def covert_remember_me_to_bool(cls, v: Optional[str]) -> bool:
        if v == "on":
            return True
        return False
