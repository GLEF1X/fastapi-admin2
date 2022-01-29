from typing import List, Type, Optional, Any, Dict

from fastapi import Depends, HTTPException
from fastapi.params import Path
from starlette.requests import Request
from starlette.status import HTTP_404_NOT_FOUND

from fastapi_admin2.exceptions import InvalidResource
from fastapi_admin2.resources import Dropdown, Link, AbstractModelResource, Resource


def get_orm_model_by_resource_name(
        request: Request,
        resource_name: str = Path(..., alias="resource")
) -> Optional[Type[Any]]:
    if not resource_name:
        return None
    for model_cls in request.app.model_resources.keys():
        if model_cls.__name__.lower() != resource_name.strip().lower():
            continue
        return model_cls
    raise HTTPException(status_code=HTTP_404_NOT_FOUND)


async def get_model_resource(
        request: Request,
        orm_model: Any = Depends(
            get_orm_model_by_resource_name
        )
) -> AbstractModelResource:
    model_resource_type = request.app.get_model_resource_type(orm_model)  # type: Optional[Type[AbstractModelResource]]
    if not model_resource_type:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)

    return await model_resource_type.from_http_request(request)


def get_resources(request: Request) -> List[Dict[str, Any]]:
    resources = request.app.resources
    r = _get_resources(resources) # TODO replace
    print(r)
    return r


def _get_resources(resources: List[Type[Resource]]):
    ret = []
    for resource in resources:
        item = {
            "icon": resource.icon,
            "label": resource.label,
        }
        if issubclass(resource, Link):
            item["type"] = "link"
            item["url"] = resource.url
            item["target"] = resource.target
        elif issubclass(resource, AbstractModelResource):
            item["type"] = "model"
            item["model"] = resource.model.__name__.lower()
        elif issubclass(resource, Dropdown):
            item["type"] = "dropdown"
            item["resources"] = _get_resources(resource.resources)
        else:
            raise InvalidResource("Should be subclass of Resource")
        ret.append(item)
    return ret
