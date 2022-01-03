import asyncio
import dataclasses
from typing import List, Type, Any, Iterable, Dict, Tuple

from fastapi import Depends, HTTPException
from fastapi.params import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
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
            for field in self._model_resource.get_model_fields_for_display()
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
            for field in self._model_resource.get_model_fields_for_display():
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
            for field in self._model_resource.get_model_fields_for_display():
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


@dataclasses.dataclass
class ModelData:
    orm_models: List[Any] = dataclasses.field(default_factory=list)
    total_entries_count: int = 0


class ModelListQuerier:

    def __init__(
            self,
            request: Request,
            model_resource: Model = Depends(get_model_resource),
            page_size: int = 10,
            model=Depends(get_model), page_num: int = 1
    ):
        self._model_resource = model_resource
        self.page_size = page_size
        self._model = model
        self._request = request
        self.page_num = page_num

    async def get_model_data(self, session: AsyncSession) -> ModelData:
        select_stmt = select(
            self._model, func.count("*").over().label("entry_count")
        ).select_from(self._model)
        select_stmt = await self._model_resource.enrich_select_with_filters(
            request=self._request,
            model=self._model,
            select_statement=select_stmt
        )

        page_size = self.page_size
        if self.page_size:
            select_stmt = select_stmt.limit(self.page_size)
        else:
            page_size = self._model_resource.page_size

        select_stmt = select_stmt.offset((self.page_num - 1) * page_size)

        rows = (await session.execute(select_stmt)).all()

        try:
            total_entries_count = rows[0][1]
            orm_models = [row[0] for row in rows]
            return ModelData(orm_models=orm_models, total_entries_count=total_entries_count)
        except IndexError:
            return ModelData()
