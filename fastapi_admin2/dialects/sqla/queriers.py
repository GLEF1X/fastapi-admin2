from typing import Any, Sized

from fastapi import Depends
from sqlalchemy import select, func, delete, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from fastapi_admin2.base.entities import ResourceList
from fastapi_admin2.depends import get_model_resource, get_model
from fastapi_admin2.dialects.sqla.markers import AsyncSessionDependencyMarker
from fastapi_admin2.dialects.sqla.toolings import include_where_condition_by_pk
from fastapi_admin2.resources.model import AbstractModelResource


async def get_resource_list(request: Request,
                            model_resource: AbstractModelResource = Depends(get_model_resource),
                            page_size: int = 10,
                            model=Depends(get_model), page_num: int = 1,
                            session: AsyncSession = Depends(AsyncSessionDependencyMarker)) -> ResourceList:
    select_stmt = select(
        model, func.count("*").over().label("entry_count")
    ).select_from(model)
    select_stmt = await model_resource.enrich_select_with_filters(
        request=request,
        model=model,
        query=select_stmt
    )

    page_size = page_size
    if page_size:
        select_stmt = select_stmt.limit(page_size)
    else:
        page_size = model_resource.page_size

    select_stmt = select_stmt.offset((page_num - 1) * page_size)

    async with session.begin():
        rows = (await session.execute(select_stmt)).all()

    try:
        total_entries_count = rows[0][1]
        orm_models = [row[0] for row in rows]
        return ResourceList(models=orm_models, total_entries_count=total_entries_count)
    except IndexError:
        return ResourceList()


async def delete_resource_by_id(id_: str, session: AsyncSession = Depends(AsyncSessionDependencyMarker),
                                model: Any = Depends(get_model)) -> None:
    stmt = include_where_condition_by_pk(delete(model), model, id_)
    async with session.begin():
        await session.execute(stmt)


async def bulk_delete_resources(ids: str, model: Any = Depends(get_model),
                                session: AsyncSession = Depends(AsyncSessionDependencyMarker)) -> None:
    stmt = include_where_condition_by_pk(delete(model), model, ids.split(","))
    async with session.begin():
        await session.execute(stmt)
