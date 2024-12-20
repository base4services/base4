import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt
import pydantic
import ujson as json
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from base4.utilities.files import get_project_root

current_file_path = str(get_project_root())
from base4.utilities.files import read_file
from fastapi import Depends, HTTPException

private_key = read_file('security/private_key.pem')
public_key = read_file('security/public_key.pem')


class DecodedToken(pydantic.BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    expire_at: datetime
    expired: bool


class CreateTokenRequest(pydantic.BaseModel):
    id_user: uuid.UUID
    id_tenant: uuid.UUID

    ttl: int = 24 * 60 * 60
    exp: Optional[int | None] = None

    def __init__(self, id_user: uuid.UUID, id_tenant: uuid.UUID, ttl: int = 24 * 68 * 60):
        super().__init__(id_user=id_user, id_tenant=id_tenant, ttl=ttl)

        self.exp = int(time.time()) + ttl


def create_token(request: CreateTokenRequest) -> str:
    global private_key
    payload = json.loads(json.dumps(request.model_dump(), default=str))

    # print(payload)
    return jwt.encode(payload, private_key, algorithm='RS256')


def decode_token(token: str) -> DecodedToken:
    global public_key
    try:
        decoded_payload = jwt.decode(token, public_key, algorithms=['RS256'])
    except Exception as e:
        raise
    if 'exp' in decoded_payload:
        exp = decoded_payload['exp']
    else:
        exp = int(time.time()) + 24 * 60 * 60  # forever

    return DecodedToken(
        user_id=decoded_payload['id_user'],
        tenant_id=decoded_payload['id_tenant'],
        #        tenant_id='3acd0b70-6bdd-4519-8b8b-851f0114c89c', #decoded_payload['id_tenant']
        expire_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        expired=int(time.time()) > exp,
    )


def verify_token(token: str = Depends(oauth2_scheme)) -> DecodedToken:

    # TODO: Treba konsultovati users servis na tenantu, koji je na basd4services/tenants ili services/tenant
    # TODO: ...

    try:
        decoded = decode_token(token)

        ...

    except Exception as e:
        raise HTTPException(status_code=401, detail={"code": "INVALID_SESSION", "parameter": "token", "message": f"error decoding token"})

    if decoded.expired:
        raise HTTPException(status_code=401, detail={"code": "SESSION_EXPIRED", "parameter": "token", "message": f"your session has been expired"})
    return decoded


def open_api_call() -> DecodedToken:  # token: Optional[str] = Depends(oauth2_scheme)) -> DecodedToken:
    return DecodedToken(
        user_id='00000000-0000-0000-0000-000000000000',
        tenant_id='00000000-0000-0000-0000-000000000000',
        expire_at=datetime.fromtimestamp(0, tz=timezone.utc),
        expired=False,
    )


def get_user_id_from_token(request: Request):
    auth = request.headers.get("Authorization")
    decoded = decode_token(auth.split(" ")[-1])
    return decoded.user_id


def get_token_from_cookie(request: Request) -> DecodedToken:
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail={"id_message": "TOKEN_NOT_FOUND", "message": "Token not found"})
    return decode_token(token)
