from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.auth import decode_user_id


def _generate_es256_token(payload: dict) -> tuple[str, object]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(payload, private_key, algorithm="ES256")
    return token, private_key.public_key()


def test_decode_user_id_from_valid_token():
    token, public_key = _generate_es256_token(
        {"sub": "11111111-1111-1111-1111-111111111111", "aud": "authenticated"}
    )
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    with patch("app.auth._jwks_client.get_signing_key_from_jwt", return_value=mock_signing_key):
        assert decode_user_id(token) == "11111111-1111-1111-1111-111111111111"


def test_decode_user_id_rejects_bad_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_user_id("not-a-real-token")
    assert exc_info.value.status_code == 401


def test_decode_user_id_rejects_token_signed_with_wrong_key():
    token, _real_public_key = _generate_es256_token(
        {"sub": "11111111-1111-1111-1111-111111111111", "aud": "authenticated"}
    )
    _other_private_key = ec.generate_private_key(ec.SECP256R1())
    wrong_public_key = _other_private_key.public_key()
    mock_signing_key = MagicMock()
    mock_signing_key.key = wrong_public_key
    with patch("app.auth._jwks_client.get_signing_key_from_jwt", return_value=mock_signing_key):
        with pytest.raises(HTTPException) as exc_info:
            decode_user_id(token)
    assert exc_info.value.status_code == 401
