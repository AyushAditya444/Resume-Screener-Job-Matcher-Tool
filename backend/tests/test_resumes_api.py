from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.main import app
from app.supabase_client import get_scoped_client

client = TestClient(app)


def _auth_headers():
    return {"Authorization": "Bearer fake-token"}


def test_create_resume_downloads_parses_and_stores():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.download.return_value = b"file-bytes"
    inserted_row = {
        "id": "resume-1",
        "storage_path": "user-1/resume.pdf",
        "original_filename": "resume.pdf",
        "parsed_text": "Jane Doe resume text",
        "extracted_skills": ["python", "sql"],
        "experience_years": 5.0,
        "education_level": "bachelor",
        "created_at": "2026-09-05T00:00:00Z",
    }
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [inserted_row]
    app.dependency_overrides[get_scoped_client] = lambda: mock_client

    with (
        patch("app.routers.resumes.extract_text", return_value="Jane Doe resume text"),
        patch("app.routers.resumes.extract_skills", return_value=["python", "sql"]),
        patch("app.routers.resumes.extract_years_of_experience", return_value=5.0),
        patch("app.routers.resumes.extract_education_level", return_value="bachelor"),
    ):
        response = client.post(
            "/resumes",
            json={"storage_path": "user-1/resume.pdf", "original_filename": "resume.pdf"},
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["extracted_skills"] == ["python", "sql"]
    assert body["experience_years"] == 5.0


def test_create_resume_returns_422_for_unreadable_file():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.download.return_value = b"garbage"
    app.dependency_overrides[get_scoped_client] = lambda: mock_client

    with patch("app.routers.resumes.extract_text", side_effect=ValueError("Could not read PDF file")):
        response = client.post(
            "/resumes",
            json={"storage_path": "user-1/bad.pdf", "original_filename": "bad.pdf"},
            headers=_auth_headers(),
        )

    assert response.status_code == 422
    assert "Could not read PDF file" in response.json()["detail"]
