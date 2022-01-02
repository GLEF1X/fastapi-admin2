from typing import Type, Any

from fastapi import APIRouter, Depends, Path
from jinja2 import TemplateNotFound
from sqlalchemy import delete as sa_delete
from sqlalchemy import select, func, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from tortoise.transactions import in_transaction

from fastapi_admin.depends import get_model, get_model_resource, get_resources, ModelResourceListPresenter
from fastapi_admin.general_dependencies import AsyncSessionDependencyMarker
from fastapi_admin.resources import Model as ModelResource
from fastapi_admin.responses import redirect
from fastapi_admin.template import templates
from fastapi_admin.utils.sqlalchemy import include_where_condition_by_pk

router = APIRouter()


@router.get("/{resource}/list")
async def list_view(
        request: Request,
        model=Depends(get_model),
        session: AsyncSession = Depends(AsyncSessionDependencyMarker),
        resources=Depends(get_resources),
        model_resource: ModelResource = Depends(get_model_resource),
        resource_name: str = Path(..., alias="resource"),
        page_size: int = 10,
        page_num: int = 1,
        field_presenter: ModelResourceListPresenter = Depends(ModelResourceListPresenter)
):
    field_labels = model_resource.get_field_labels()
    select_stmt = select(model)
    params, select_stmt = await model_resource.enrich_select_with_filters(
        request,
        model,
        dict(request.query_params),
        select_stmt
    )
    filters = await model_resource.render_filters(request, params)
    total = (await session.execute(select(func.count("*")).select_from(select_stmt))).scalar()
    if page_size:
        select_stmt = select_stmt.limit(page_size)
    else:
        page_size = model_resource.page_size
    select_stmt = select_stmt.offset((page_num - 1) * page_size)
    orm_models = (await session.execute(select_stmt)).scalars().all()
    rendered_fields = await field_presenter.render_payload_for_resource(orm_models)
    context = {
        "request": request,
        "resources": resources,
        "fields_label": field_labels,
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
        "total": total,
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
async def update(
        request: Request,
        resource: str = Path(...),
        pk: str = Path(...),
        model_resource: ModelResource = Depends(get_model_resource),
        resources=Depends(get_resources),
        model=Depends(get_model),
        session: AsyncSession = Depends(AsyncSessionDependencyMarker)
):
    form = await request.form()
    data, m2m_data = await model_resource.resolve_data(request, form)
    async with in_transaction() as conn:
        obj = (
            await model.filter(pk=pk)
                .using_db(conn)
                .select_for_update()
                .get()
                .prefetch_related(*model_resource.get_m2m_field())
        )
        await obj.update_from_dict(data).save(using_db=conn)
        for k, items in m2m_data.items():
            m2m_obj = getattr(obj, k)
            await m2m_obj.clear()
            if items:
                await m2m_obj.add(*items)
        obj = (
            await model.filter(pk=pk)
                .using_db(conn)
                .get()
                .prefetch_related(*model_resource.get_m2m_field())
        )
    inputs = await model_resource.render_inputs(request, obj)
    if "save" not in form.keys():
        return redirect(request, "list_view", resource=resource)
    context = {
        "request": request,
        "resources": resources,
        "resource_label": model_resource.label,
        "resource": resource,
        "model_resource": model_resource,
        "inputs": inputs,
        "pk": pk,
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
async def create(
        request: Request,
        resource: str = Path(...),
        resources=Depends(get_resources),
        model_resource: ModelResource = Depends(get_model_resource),
        model: Type[Any] = Depends(get_model),
        session: AsyncSession = Depends(AsyncSessionDependencyMarker)
):
    inputs = await model_resource.render_inputs(request)
    form = await request.form()
    data, m2m_data = await model_resource.resolve_data(request, form)
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


@router.delete("/{resource}/delete/{id}")
async def delete(request: Request, id: str, model: Any = Depends(get_model),
                 session: AsyncSession = Depends(AsyncSessionDependencyMarker)):
    async with session.begin():
        await session.execute(sa_delete(model).where(inspect(model).primary_key[0] == id))
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)


@router.delete("/{resource}/delete")
async def bulk_delete(request: Request, ids: str, model: Any = Depends(get_model),
                      session: AsyncSession = Depends(AsyncSessionDependencyMarker)):
    async with session.begin():
        stmt = include_where_condition_by_pk(sa_delete(model), model, ids.split(","))
        await session.execute(stmt)
    return RedirectResponse(url=request.headers.get("referer"), status_code=HTTP_303_SEE_OTHER)
