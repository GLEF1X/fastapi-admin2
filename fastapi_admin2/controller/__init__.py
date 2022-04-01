import abc
from typing import List, Dict, Any

from fastapi import Depends, Path
from starlette.templating import Jinja2Templates

from fastapi_admin2.depends import get_resources, get_model_resource
from fastapi_admin2.resources import AbstractModelResource


class BaseAdminController(abc.ABC):

    def __init__(self, templates: Jinja2Templates):
        self._templates = templates

    @abc.abstractmethod
    async def show_list_of_entities(
            self,
            resources: List[Dict[str, Any]] = Depends(get_resources),
            model_resource: AbstractModelResource = Depends(get_model_resource),
            resource_name: str = Path(..., alias="resource"),
            page_size: int = 10,
            page_num: int = 1
    ):
        pass


