from typing import Optional, Any

from pydantic import BaseModel, validator

from fastapi_admin.enums import HTTPMethod


class Action(BaseModel):
    icon: str
    label: str
    name: str
    method: HTTPMethod = HTTPMethod.POST
    ajax: bool = True

    @validator("ajax")
    def ajax_validate(cls, v: bool, values: dict, **kwargs: Any):
        if not v and values["method"] != HTTPMethod.GET:
            raise ValueError("ajax is False only available when method is Method.GET")


class ToolbarAction(Action):
    class_: Optional[str]