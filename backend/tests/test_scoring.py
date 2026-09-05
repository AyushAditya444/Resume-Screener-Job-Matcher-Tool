from unittest.mock import patch

from app.services.scoring import score_resume_against_posting


def test_full_skill_overlap_and_experience_met():
    with patch("app.services.scoring.semantic_similarity", return_value=80.0):
        result = score_resume_against_posting(
            resume_text="...",
            resume_skills=["python", "sql", "react"],
            resume_years=5.0,
            posting_text="...",
            posting_skills=["python", "sql"],
            min_years=3.0,
        )
    assert result.skill_score == 100.0
    assert result.semantic_score == 80.0
    assert result.overall_score == round(0.6 * 80.0 + 0.4 * 100.0, 2)
    assert set(result.skills_matched) == {"python", "sql"}
    assert result.skills_missing == []
    assert result.experience_match is True


def test_partial_skill_overlap_and_experience_not_met():
    with patch("app.services.scoring.semantic_similarity", return_value=50.0):
        result = score_resume_against_posting(
            resume_text="...",
            resume_skills=["python"],
            resume_years=1.0,
            posting_text="...",
            posting_skills=["python", "sql", "docker"],
            min_years=3.0,
        )
    assert result.skill_score == round(1 / 3 * 100, 2)
    assert set(result.skills_matched) == {"python"}
    assert set(result.skills_missing) == {"sql", "docker"}
    assert result.experience_match is False


def test_no_required_skills_gives_full_skill_score():
    with patch("app.services.scoring.semantic_similarity", return_value=70.0):
        result = score_resume_against_posting(
            resume_text="...",
            resume_skills=["python"],
            resume_years=None,
            posting_text="...",
            posting_skills=[],
            min_years=None,
        )
    assert result.skill_score == 100.0
    assert result.experience_match is None
