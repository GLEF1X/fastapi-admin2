from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class AbstractAdmin:
    id: int
    username: str
    password: str
    avatar: str


@dataclass
class ResourceList:
    models: Sequence[Any] = ()
    total_entries_count: int = 0
