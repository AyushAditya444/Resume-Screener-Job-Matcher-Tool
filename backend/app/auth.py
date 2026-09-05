import jwt
from fastapi import Header, HTTPException

from app.config import settings

# Supabase projects now sign user session tokens with an asymmetric key
# (ES256) rather than the legacy shared HS256 secret - verifying against a
# static secret rejects every real token. Fetching the public signing key
# from Supabase's JWKS endpoint (matched by the token's `kid`) works for
# both the current key and any still-valid previously-rotated key.
_jwks_client = jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def decode_user_id(token: str) -> str:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return payload["sub"]


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    return decode_user_id(token)


def get_bearer_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ")
