from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.main import app
from app.supabase_client import get_scoped_client

client = TestClient(app)


def test_create_job_posting_extracts_required_skills():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    mock_client = MagicMock()
    inserted_row = {
        "id": "posting-1",
        "title": "Backend Engineer",
        "company": "Acme",
        "raw_text": "Need Python and Docker experience",
        "required_skills": ["python", "docker"],
        "min_experience_years": 3.0,
        "created_at": "2026-09-05T00:00:00Z",
    }
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [inserted_row]
    app.dependency_overrides[get_scoped_client] = lambda: mock_client

    with patch("app.routers.job_postings.extract_skills", return_value=["python", "docker"]):
        response = client.post(
            "/job-postings",
            json={
                "title": "Backend Engineer",
                "company": "Acme",
                "raw_text": "Need Python and Docker experience",
                "min_experience_years": 3.0,
            },
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 201
    assert response.json()["required_skills"] == ["python", "docker"]


def test_create_job_posting_rejects_empty_text():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_scoped_client] = lambda: MagicMock()

    response = client.post(
        "/job-postings",
        json={"title": "Backend Engineer", "raw_text": "   "},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422
