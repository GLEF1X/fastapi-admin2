from typing import Type, Any

from fastapi import APIRouter, Depends, Path
from jinja2 import TemplateNotFound
from sqlalchemy import delete as sa_delete
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from fastapi_admin.depends import get_model, get_model_resource, get_resources, ModelResourceListPresenter, \
    ModelListQuerier
from fastapi_admin.general_dependencies import AsyncSessionDependencyMarker
from fastapi_admin.resources import Model as ModelResource
from fastapi_admin.responses import redirect
from fastapi_admin.template import templates
from fastapi_admin.utils.atomic import atomic, AtomicSession
from fastapi_admin.utils.sqlalchemy import include_where_condition_by_pk

router = APIRouter()


@router.get("/{resource}/list")
@atomic
async def list_view(
        request: Request,
        resources=Depends(get_resources),
        model_resource: ModelResource = Depends(get_model_resource),
        resource_name: str = Path(..., alias="resource"),
        page_size: int = 10,
        page_num: int = 1,
        field_presenter: ModelResourceListPresenter = Depends(ModelResourceListPresenter),
        model_list_querier: ModelListQuerier = Depends(ModelListQuerier),
        session: AsyncSession = Depends(AtomicSession)
):
    model_data = await model_list_querier.get_model_data(session)
    parsed_query_params = await model_resource.parse_query_params(request)
    filters = await model_resource.render_filters(request, parsed_query_params)

    rendered_fields = await field_presenter.render_payload_for_resource(model_data.orm_models)
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
        "total": model_data.total_entries_count,
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


@router.post("/{resource}/update/{pk}")
async def update(request: Request):
    # TODO fill out this view
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)


@router.get("/{resource}/update/{id}")
async def update_view(
        request: Request,
        resource: str = Path(...),
        id_: str = Path(..., alias="id"),
        model_resource: ModelResource = Depends(get_model_resource),
        resources=Depends(get_resources),
        model=Depends(get_model),
        session: AsyncSession = Depends(AsyncSessionDependencyMarker)
):
    async with session.begin():
        obj = await session.get(model, id_)
    inputs = await model_resource.render_inputs(request, obj)
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
        model_resource: ModelResource = Depends(get_model_resource),
):
    inputs = await model_resource.render_inputs(request)
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
@atomic
async def create(
        request: Request,
        resource: str = Path(...),
        resources=Depends(get_resources),
        model_resource: ModelResource = Depends(get_model_resource),
        model: Type[Any] = Depends(get_model),
        session: AsyncSession = Depends(AtomicSession)
):
    inputs = await model_resource.render_inputs(request)
    form = await request.form()
    data, m2m_data = await model_resource.resolve_data(request, form)

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


@router.delete("/{resource}/delete/{id}")
@atomic
async def delete(request: Request, id: str, model: Any = Depends(get_model),
                 session: AsyncSession = Depends(AtomicSession)):
    await session.execute(sa_delete(model).where(inspect(model).primary_key[0] == id))
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)


@router.delete("/{resource}/delete")
@atomic
async def bulk_delete(request: Request, ids: str, model: Any = Depends(get_model),
                      session: AsyncSession = Depends(AtomicSession)):
    stmt = include_where_condition_by_pk(sa_delete(model), model, ids.split(","))
    await session.execute(stmt)
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)
