from sqlalchemy import Column, VARCHAR, BIGINT, Identity

from fastapi_admin.database.models.base import OrmModelBase


class Admin(OrmModelBase):
    __abstract__ = True

    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    username = Column(VARCHAR(50), unique=True)
    password = Column(VARCHAR(200), nullable=False, )
    avatar = Column(VARCHAR(200), nullable=True)
