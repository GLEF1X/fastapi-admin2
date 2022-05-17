from typing import Any

from fastapi import Depends
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlapagination import JoinBasedPaginator
from starlette.requests import Request

from fastapi_admin2.backends.sqla.markers import AsyncSessionDependencyMarker
from fastapi_admin2.backends.sqla.toolings import include_where_condition_by_pk
from fastapi_admin2.depends import get_model_resource, get_orm_model_by_resource_name
from fastapi_admin2.domain.entities import ResourceList, PagingMetadata
from fastapi_admin2.ui.resources.model import AbstractModelView


async def get_resource_list(request: Request,
                            model_resource: AbstractModelView = Depends(get_model_resource),
                            page_size: int = 10,
                            model=Depends(get_orm_model_by_resource_name), page_num: int = 1,
                            session: AsyncSession = Depends(AsyncSessionDependencyMarker)) -> ResourceList:
    select_stmt = select(
        model, func.count("*").over().label("entry_count")
    ).select_from(model)
    select_stmt = await model_resource.enrich_select_with_filters(
        request=request,
        model=model,
        query=select_stmt
    )

    paginator = JoinBasedPaginator(select_stmt, page_size, bookmark={
        "offset": (page_num - 1) * page_size
    })
    select_stmt = paginator.get_modified_sql_statement()

    async with session.begin():
        rows = (await session.execute(select_stmt)).all()
        page = paginator.parse_result(rows)

    try:
        return ResourceList(
            models=list(page),
            paging_meta=PagingMetadata(
                page_size=page_size,
                page_num=page_num,
                total_pages=page.total_pages_count,
            )
        )
    except IndexError:
        return ResourceList(paging_meta=PagingMetadata(page_size=page_size))


async def delete_resource_by_id(id_: str, session: AsyncSession = Depends(AsyncSessionDependencyMarker),
                                model: Any = Depends(get_orm_model_by_resource_name)) -> None:
    stmt = include_where_condition_by_pk(delete(model), model, id_,
                                         dialect_name=session.bind.dialect.name)
    async with session.begin():
        await session.execute(stmt)


async def bulk_delete_resources(ids: str, model: Any = Depends(get_orm_model_by_resource_name),
                                session: AsyncSession = Depends(AsyncSessionDependencyMarker)) -> None:
    stmt = include_where_condition_by_pk(delete(model), model, ids.split(","),
                                         dialect_name=session.bind.dialect.name)
    async with session.begin():
        await session.execute(stmt)
