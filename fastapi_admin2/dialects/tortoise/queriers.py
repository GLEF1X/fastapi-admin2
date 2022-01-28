from typing import Any

from fastapi import Depends
from starlette.requests import Request
from tortoise import Model

from fastapi_admin2.base.entities import ResourceList
from fastapi_admin2.depends import get_model_resource, get_model
from fastapi_admin2.resources import AbstractModelResource


async def get_resource_list(request: Request,
                            model_resource: AbstractModelResource = Depends(get_model_resource),
                            page_size: int = 10,
                            model: Model = Depends(get_model), page_num: int = 1) -> ResourceList:
    qs = model.all()
    qs = await model_resource.enrich_select_with_filters(request, model, query=qs)

    total = await qs.count()

    if page_size:
        qs = qs.limit(page_size)
    else:
        page_size = model_resource.page_size

    qs = qs.offset((page_num - 1) * page_size)

    return ResourceList(models=await qs, total_entries_count=total)


async def delete_one_by_id(id_: Any, model: Model = Depends(get_model)) -> None:
    await model.filter(pk=id_).delete()


async def bulk_delete_resources(ids: str, model: Model = Depends(get_model)) -> None:
    await model.filter(pk__in=ids.split(",")).delete()
