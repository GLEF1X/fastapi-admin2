from typing import Type, Any, List, Dict

from fastapi import APIRouter, Depends, Path
from jinja2 import TemplateNotFound
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.status import HTTP_303_SEE_OTHER

from fastapi_admin2.base.entities import ResourceList
from fastapi_admin2.depends import get_orm_model_by_resource_name, get_model_resource, get_resources
from fastapi_admin2.backends.sqla.markers import AsyncSessionDependencyMarker
from fastapi_admin2.resources import AbstractModelResource
from fastapi_admin2.responses import redirect
from fastapi_admin2.routes.dependencies import ModelListDependencyMarker, DeleteOneDependencyMarker, \
    DeleteManyDependencyMarker
from fastapi_admin2.template import templates

router = APIRouter()


@router.get("/{resource}/list")
async def list_view(
        request: Request,
        resources: List[Dict[str, Any]] = Depends(get_resources),
        model_resource: AbstractModelResource = Depends(get_model_resource),
        resource_name: str = Path(..., alias="resource"),
        page_size: int = 10,
        page_num: int = 1,
        resource_list: ResourceList = Depends(ModelListDependencyMarker)
) -> Response:
    parsed_query_params = await model_resource.parse_query_params(request)
    filters = await model_resource.render_filters(parsed_query_params)
    rendered_fields = await model_resource.render_fields(resource_list.models, request)

    context = {
        "request": request,
        "resources": resources,
        "fields_label": model_resource.get_field_labels(),
        "row_attributes": rendered_fields.row_attributes,
        "column_css_attributes": rendered_fields.column_attributes,
        "cell_css_attributes": rendered_fields.cell_attributes,
        "rendered_values": rendered_fields.rows,
        "filters": filters,
        "resource": resource_name,
        "model_resource": model_resource,
        "resource_label": model_resource.label,
        "page_size": page_size,
        "page_num": page_num,
        "total": resource_list.total_entries_count,
        "from": page_size * (page_num - 1) + 1,
        "to": page_size * page_num,
        "page_title": model_resource.page_title,
        "page_pre_title": model_resource.page_pre_title,
    }
    try:
        return templates.TemplateResponse(
            f"{resource_name}/list.html",
            context=context,
        )
    except TemplateNotFound:
        return templates.TemplateResponse(
            "list.html",
            context=context,
        )


@router.post("/{resource_name}/update/{pk}")
async def update(request: Request, resource_name: str = Path(...), pk: int = Path(...)):
    # TODO fill out this view
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)


@router.get("/{resource}/update/{id}")
async def update_view(
        request: Request,
        resource: str = Path(...),
        id_: str = Path(..., alias="id"),
        model_resource: AbstractModelResource = Depends(get_model_resource),
        resources=Depends(get_resources),
        model=Depends(get_orm_model_by_resource_name),
        session: AsyncSession = Depends(AsyncSessionDependencyMarker)
):
    async with session.begin():
        obj = await session.get(model, id_)

    inputs = await model_resource.render_inputs(obj)
    context = {
        "request": request,
        "resources": resources,
        "resource_label": model_resource.label,
        "resource": resource,
        "inputs": inputs,
        "pk": id_,
        "model_resource": model_resource,
        "page_title": model_resource.page_title,
        "page_pre_title": model_resource.page_pre_title,
    }
    try:
        return templates.TemplateResponse(
            f"{resource}/update.html",
            context=context,
        )
    except TemplateNotFound:
        return templates.TemplateResponse(
            "update.html",
            context=context,
        )


@router.get("/{resource}/create")
async def create_view(
        request: Request,
        resource: str = Path(...),
        resources=Depends(get_resources),
        model_resource: AbstractModelResource = Depends(get_model_resource),
):
    inputs = await model_resource.render_inputs()
    context = {
        "request": request,
        "resources": resources,
        "resource_label": model_resource.label,
        "resource": resource,
        "inputs": inputs,
        "model_resource": model_resource,
        "page_title": model_resource.page_title,
        "page_pre_title": model_resource.page_pre_title,
    }
    try:
        return templates.TemplateResponse(
            f"{resource}/create.html",
            context=context,
        )
    except TemplateNotFound:
        return templates.TemplateResponse(
            "create.html",
            context=context,
        )


@router.post("/{resource}/create")
async def create(
        request: Request,
        resource: str = Path(...),
        resources=Depends(get_resources),
        model_resource: AbstractModelResource = Depends(get_model_resource),
        model: Type[Any] = Depends(get_orm_model_by_resource_name),
        session: AsyncSession = Depends(AsyncSessionDependencyMarker)
):
    inputs = await model_resource.render_inputs()
    form = await request.form()
    data, m2m_data = await model_resource.resolve_form_data(form)

    async with session.begin():
        session.add(model(**data))

    if "save" in form.keys():
        return redirect(request, "list_view", resource=resource)
    context = {
        "request": request,
        "resources": resources,
        "resource_label": model_resource.label,
        "resource": resource,
        "inputs": inputs,
        "model_resource": model_resource,
        "page_title": model_resource.page_title,
        "page_pre_title": model_resource.page_pre_title,
    }
    try:
        return templates.TemplateResponse(
            f"{resource}/create.html",
            context=context,
        )
    except TemplateNotFound:
        return templates.TemplateResponse(
            "create.html",
            context=context,
        )


@router.delete("/{resource}/delete/{id}", dependencies=[Depends(DeleteOneDependencyMarker)])
async def delete(request: Request):
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)


@router.delete("/{resource}/delete", dependencies=[Depends(DeleteManyDependencyMarker)])
async def bulk_delete(request: Request):
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)
