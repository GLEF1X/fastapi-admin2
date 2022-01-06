from typing import Type, Any

from fastapi import APIRouter, Depends, Path
from jinja2 import TemplateNotFound
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from fastapi_admin.base.entities import ResourceList
from fastapi_admin.depends import get_model, get_model_resource, get_resources, get_current_admin
from fastapi_admin.dialects.sqla.markers import AsyncSessionDependencyMarker
from fastapi_admin.resources import AbstractModelResource
from fastapi_admin.responses import redirect
from fastapi_admin.routes.dependencies import ModelListDependencyMarker, DeleteOneDependencyMarker, \
    DeleteManyDependencyMarker
from fastapi_admin.stylists.model_list import ModelResourceListStylist
from fastapi_admin.template import templates

router = APIRouter(dependencies=[Depends(get_current_admin)])


@router.get("/{resource}/list")
async def list_view(
        request: Request,
        resources=Depends(get_resources),
        model_resource: AbstractModelResource = Depends(get_model_resource),
        resource_name: str = Path(..., alias="resource"),
        page_size: int = 10,
        page_num: int = 1,
        field_presenter: ModelResourceListStylist = Depends(ModelResourceListStylist),
        resource_list: ResourceList = Depends(ModelListDependencyMarker)
):
    parsed_query_params = await model_resource.parse_query_params(request)
    filters = await model_resource.render_filters(parsed_query_params)
    rendered_fields = await field_presenter.render_payload_for_resource(resource_list.models)

    context = {
        "request": request,
        "resources": resources,
        "fields_label": model_resource.get_field_labels(),
        "row_attributes": rendered_fields.row_attributes,
        "column_attributes": rendered_fields.column_attributes,
        "cell_attributes": rendered_fields.cell_attributes,
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
        model=Depends(get_model),
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
        model: Type[Any] = Depends(get_model),
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
