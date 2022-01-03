from fastapi_admin.database.repository.admin import AdminRepositoryProto
from fastapi_admin.utils.depends import Marker


class AdminRepositoryDependencyMarker(Marker[AdminRepositoryProto]):
    pass
