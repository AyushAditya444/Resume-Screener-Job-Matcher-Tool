import jwt
import pytest
from fastapi import HTTPException

from app.auth import decode_user_id
from app.config import settings


def test_decode_user_id_from_valid_token():
    token = jwt.encode(
        {"sub": "11111111-1111-1111-1111-111111111111", "aud": "authenticated"},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    assert decode_user_id(token) == "11111111-1111-1111-1111-111111111111"


def test_decode_user_id_rejects_bad_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_user_id("not-a-real-token")
    assert exc_info.value.status_code == 401
