from enum import Enum


class LookupsSingle(object):
    def __init__(self, id, code):
        self.id = id
        self.code = code


class BaseEnum(Enum):
    def __init__(self, id, code):
        self.lookup = LookupsSingle(id, code)

    @classmethod
    def by_code(cls, code):
        for item in cls:
            if item.lookup.code == code:
                return item.lookup
        raise ValueError(f"No item with code '{code}' found in {cls.__name__}.")

    @classmethod
    def by_id(cls, id):
        for item in cls:
            if item.lookup.id == id:
                return item.lookup
        raise ValueError(f"No item with id '{id}' found in {cls.__name__}.")
