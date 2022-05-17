from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class AbstractAdmin:
    id: int
    username: str
    password: str
    profile_pic: str


@dataclass
class PagingMetadata:
    page_size: int
    page_num: int = 0
    total_pages: int = 0
    from_item: int = 0
    to_item: int = 0


@dataclass
class ResourceList:
    paging_meta: PagingMetadata
    models: Sequence[Any] = ()
