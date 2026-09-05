from unittest.mock import patch

from app.supabase_client import get_scoped_client


def test_scoped_client_sets_auth_token():
    with patch("app.supabase_client.create_client") as mock_create:
        mock_client = mock_create.return_value
        result = get_scoped_client(token="user-jwt-123")
        mock_client.postgrest.auth.assert_called_once_with("user-jwt-123")
        mock_client.storage.session.headers.update.assert_called_once_with(
            {"Authorization": "Bearer user-jwt-123"}
        )
        assert result is mock_client
