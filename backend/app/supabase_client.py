from fastapi import Depends
from supabase import Client, create_client

from app.auth import get_bearer_token
from app.config import settings


def get_scoped_client(token: str = Depends(get_bearer_token)) -> Client:
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(token)
    client.storage.session.headers.update({"Authorization": f"Bearer {token}"})
    return client
