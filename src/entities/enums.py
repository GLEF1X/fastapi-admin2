from enum import Enum, IntEnum


class ProductType(IntEnum):
    article = 1
    page = 2


class Status(IntEnum):
    on = 1
    off = 0

    def switch_status(self):
        if self.value == 1:
            return self.off
        else:
            return self.on


class Action(str, Enum):
    create = "create"
    delete = "delete"
    edit = "edit"
