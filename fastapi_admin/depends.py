import asyncio
import dataclasses
from typing import List, Type, Any, Iterable, Dict

from fastapi import Depends, HTTPException
from fastapi.params import Path
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from fastapi_admin.database.models.abstract_admin import AbstractAdmin
from fastapi_admin.exceptions import InvalidResource
from fastapi_admin.resources import Dropdown, Link, Model, Resource, ComputeField


def get_model(request: Request, resource_name: str = Path(..., alias="resource")):
    if not resource_name:
        return None
    for model_cls in request.app.model_resources.keys():
        if model_cls.__name__.lower() != resource_name:
            continue
        return model_cls
    raise HTTPException(status_code=HTTP_404_NOT_FOUND)


async def get_model_resource(request: Request, model=Depends(get_model)) -> Model:
    model_resource = request.app.get_model_resource(model)  # type: Model
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
        elif issubclass(resource, Model):
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


@dataclasses.dataclass(frozen=True)
class RenderedFields:
    rows: List[List[Any]]  # TODO rename to human-readable
    row_attributes: Iterable[dict]
    column_attributes: Iterable[dict]
    cell_attributes: Iterable[Iterable[dict]]


class ModelResourceListPresenter:
    def __init__(self, request: Request, model_resource: Model = Depends(get_model_resource)):
        self._request = request
        self._model_resource = model_resource

    async def render_payload_for_resource(self, values: List[Any], display: bool = True) -> RenderedFields:
        result = await asyncio.gather(
            self._generate_row_mappings(values, display),
            self._generate_css_attributes_for_rows(values),
            self._generate_css_attributes_for_columns(),
            self._generate_css_for_cells(values)
        )
        return RenderedFields(*result)

    async def _generate_css_attributes_for_columns(self) -> Iterable[Dict[Any, Any]]:
        return await asyncio.gather(*[
            self._model_resource.column_attributes(self._request, field)
            for field in self._model_resource.get_model_fields()
        ])

    async def _generate_css_attributes_for_rows(self, values: List[Any]) -> Iterable[Dict[Any, Any]]:
        return await asyncio.gather(*[
            self._model_resource.row_attributes(self._request, orm_model_instance)
            for orm_model_instance in values
        ])

    async def _generate_css_for_cells(self, values: List[Any]) -> List[List[dict]]:
        result = []
        for orm_model_instance in values:
            cell_attributes = []
            for field in self._model_resource.get_model_fields():
                cell_attributes.append(
                    await self._model_resource.cell_attributes(
                        self._request, orm_model_instance, field
                    )
                )
            result.append(cell_attributes)
        return result

    async def _generate_row_mappings(self, values: List[Any], display: bool = True):
        result = []
        for orm_model_instance in values:
            row = []
            for field in self._model_resource.get_model_fields():
                if isinstance(field, ComputeField):
                    field_value = await field.get_value(self._request, orm_model_instance)
                else:
                    field_value = getattr(orm_model_instance, field.name, None)

                if display:
                    row.append(await field.display.render(self._request, field_value))
                else:
                    row.append(await field.input.render(self._request, field_value))
            result.append(row)
        return result
