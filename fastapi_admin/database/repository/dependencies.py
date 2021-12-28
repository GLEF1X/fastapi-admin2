from sqlalchemy.orm import sessionmaker

from fastapi_admin.utils.depends import Marker


class SessionPoolDependencyMarker(Marker[sessionmaker]):
    pass
