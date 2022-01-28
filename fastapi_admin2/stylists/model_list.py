import asyncio
import dataclasses
from typing import List, Any, Iterable, Dict, Sequence

from fastapi import Depends
from starlette.requests import Request

from fastapi_admin2.depends import get_model_resource
from fastapi_admin2.resources import AbstractModelResource, ComputeField


@dataclasses.dataclass(frozen=True)
class RenderedFields:
    rows: List[List[Any]]  # TODO rename to human-readable
    row_attributes: Iterable[dict]
    column_attributes: Iterable[dict]
    cell_attributes: Iterable[Iterable[dict]]


class ModelResourceListStylist:
    def __init__(self, request: Request, model_resource: AbstractModelResource = Depends(get_model_resource)):
        self._request = request
        self._model_resource = model_resource

    async def render_payload_for_resource(self, values: Sequence[Any],
                                          display: bool = True) -> RenderedFields:
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

    async def _generate_css_attributes_for_rows(self, values: Sequence[Any]) -> Iterable[Dict[Any, Any]]:
        return await asyncio.gather(*[
            self._model_resource.row_attributes(self._request, orm_model_instance)
            for orm_model_instance in values
        ])

    async def _generate_css_for_cells(self, values: Sequence[Any]) -> List[List[dict]]:
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

    async def _generate_row_mappings(self, values: Sequence[Any], display: bool = True):
        result = []
        for orm_model_instance in values:
            row = []
            for field in self._model_resource.get_model_fields_for_display():
                if isinstance(field, ComputeField):
                    field_value = await field.get_value(self._request, orm_model_instance)
                else:
                    field_value = getattr(orm_model_instance, field.name, None)

                if display:
                    row.append(await field.display.render(field_value))
                else:
                    row.append(await field.input.render(field_value))
            result.append(row)
        return result
