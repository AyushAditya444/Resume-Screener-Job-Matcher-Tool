from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.auth import get_current_user_id
from app.main import app
from app.services.scoring import ScoreResult
from app.supabase_client import get_scoped_client

client = TestClient(app)


def _mock_client_with_data(resumes, posting):
    mock_client = MagicMock()

    def table_side_effect(name):
        table_mock = MagicMock()
        if name == "resumes":
            table_mock.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = resumes
        elif name == "job_postings":
            table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value.data = posting
        elif name == "screening_results":
            table_mock.insert.return_value.execute.return_value.data = [
                {
                    "id": "result-1",
                    "resume_id": resumes[0]["id"] if resumes else None,
                    "overall_score": 88.0,
                    "semantic_score": 80.0,
                    "skill_score": 100.0,
                    "skills_matched": ["python"],
                    "skills_missing": [],
                    "experience_match": True,
                    "created_at": "2026-09-05T00:00:00Z",
                }
            ]
        return table_mock

    mock_client.table.side_effect = table_side_effect
    return mock_client


def test_screens_single_resume_successfully():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    resumes = [{"id": "resume-1", "parsed_text": "...", "extracted_skills": ["python"], "experience_years": 5.0}]
    posting = {"id": "posting-1", "raw_text": "...", "required_skills": ["python"], "min_experience_years": 3.0}
    app.dependency_overrides[get_scoped_client] = lambda: _mock_client_with_data(resumes, posting)

    with patch("app.routers.screenings.score_resume_against_posting") as mock_score:
        mock_score.return_value = ScoreResult(
            overall_score=88.0, semantic_score=80.0, skill_score=100.0,
            skills_matched=["python"], skills_missing=[], experience_match=True,
        )
        response = client.post(
            "/screenings",
            json={"resume_ids": ["resume-1"], "job_posting_id": "posting-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["overall_score"] == 88.0
    assert body[0]["error"] is None


def test_rejects_batch_over_20_resumes():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    app.dependency_overrides[get_scoped_client] = lambda: MagicMock()

    response = client.post(
        "/screenings",
        json={"resume_ids": [f"resume-{i}" for i in range(21)], "job_posting_id": "posting-1"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422


def test_partial_failure_does_not_fail_whole_batch():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    resumes = [{"id": "resume-1", "parsed_text": "...", "extracted_skills": [], "experience_years": None}]
    posting = {"id": "posting-1", "raw_text": "...", "required_skills": [], "min_experience_years": None}
    app.dependency_overrides[get_scoped_client] = lambda: _mock_client_with_data(resumes, posting)

    with patch("app.routers.screenings.score_resume_against_posting", side_effect=[Exception("boom")]):
        response = client.post(
            "/screenings",
            json={"resume_ids": ["resume-1"], "job_posting_id": "posting-1"},
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body[0]["error"] == "boom"
    assert body[0]["overall_score"] is None
