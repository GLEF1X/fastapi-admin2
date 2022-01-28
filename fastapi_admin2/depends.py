from typing import List, Type

from fastapi import Depends, HTTPException
from fastapi.params import Path
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from fastapi_admin2.base.entities import AbstractAdmin
from fastapi_admin2.exceptions import InvalidResource
from fastapi_admin2.resources import Dropdown, Link, AbstractModelResource, Resource


def get_model(request: Request, resource_name: str = Path(..., alias="resource")):
    if not resource_name:
        return None
    for model_cls in request.app.model_resources.keys():
        if model_cls.__name__.lower() != resource_name:
            continue
        return model_cls
    raise HTTPException(status_code=HTTP_404_NOT_FOUND)


async def get_model_resource(request: Request, model=Depends(get_model)) -> AbstractModelResource:
    model_resource = request.app.get_model_resource(model)  # type: AbstractModelResource
    if not model_resource:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    actions = await model_resource.get_actions(request)
    bulk_actions = await model_resource.get_bulk_actions(request)
    toolbar_actions = await model_resource.get_toolbar_actions(request)
    setattr(model_resource, "toolbar_actions", toolbar_actions)
    setattr(model_resource, "actions", actions)
    setattr(model_resource, "bulk_actions", bulk_actions)
    return model_resource


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


def get_resources(request: Request) -> List[dict]:
    resources = request.app.resources
    return _get_resources(resources)


def get_current_admin(request: Request) -> AbstractAdmin:
    admin = request.state.admin
    if not admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)
    return admin