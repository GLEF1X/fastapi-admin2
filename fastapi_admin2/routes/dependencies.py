from fastapi_admin2.base.entities import ResourceList
from fastapi_admin2.utils.depends import DependencyMarker


class ModelListDependencyMarker(DependencyMarker[ResourceList]):
    pass


class DeleteOneDependencyMarker(DependencyMarker[None]):
    pass


class DeleteManyDependencyMarker(DependencyMarker[None]):
    pass
