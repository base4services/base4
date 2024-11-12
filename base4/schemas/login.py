import datetime
import uuid

import pydantic


class LoginRequest(pydantic.BaseModel):
    username: str
    password: str


class LoginResponse(pydantic.BaseModel):
    token: str


class MeResponse(pydantic.BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    profile_image_url: str
    default_language: str

    active_tenant_code: str
    available_tenant_codes: list[str]

    token_expiration_timestamp: datetime.datetime
    ttl: int
