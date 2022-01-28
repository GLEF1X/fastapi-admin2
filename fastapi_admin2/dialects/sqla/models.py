from sqlalchemy import Identity, VARCHAR, Column, BIGINT
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SqlalchemyAdminModel(Base):
    __abstract__ = True

    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    username = Column(VARCHAR(50), unique=True)
    password = Column(VARCHAR(200), nullable=False)
    avatar = Column(VARCHAR(200), nullable=True)
