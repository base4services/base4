from enum import Enum

class BaseEnum(Enum):

    @classmethod
    def is_exist(cls, val=None, name=None):
        if val:
            return val in [i.value for i in cls]
        if name:
            return name in [i.name for i in cls]

    @classmethod
    def as_obj_list(cls):
        response = []
        for i in cls:
            response.append({'name': i.name, 'id': i.value})
        return response

    @classmethod
    def as_int_list(cls):
        return [i.value for i in cls]

    @classmethod
    def as_str_list(cls):
        return [i.name for i in cls]