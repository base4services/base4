from typing import Optional

import pydantic

NOT_SET = '__NOT_SET__'


class Base(pydantic.BaseModel):
    created_by: Optional[None | str] = None
    last_updated_by: Optional[None | str] = None

    def is_equal(self, other):

        keys = self.__fields__.keys()
        for f in keys:
            if getattr(self, f) in (None, NOT_SET) and getattr(other, f) in (None, NOT_SET):
                continue
            if getattr(self, f) != getattr(other, f):
                return False

        return True

    def unq(self):
        return {}
