from dataclasses import dataclass

from app.services.embeddings import semantic_similarity

SEMANTIC_WEIGHT = 0.6
SKILL_WEIGHT = 0.4


@dataclass
class ScoreResult:
    overall_score: float
    semantic_score: float
    skill_score: float
    skills_matched: list[str]
    skills_missing: list[str]
    experience_match: bool | None


def score_resume_against_posting(
    resume_text: str,
    resume_skills: list[str],
    resume_years: float | None,
    posting_text: str,
    posting_skills: list[str],
    min_years: float | None,
) -> ScoreResult:
    semantic_score = semantic_similarity(resume_text, posting_text)

    resume_skill_set = set(resume_skills)
    posting_skill_set = set(posting_skills)
    skills_matched = sorted(resume_skill_set & posting_skill_set)
    skills_missing = sorted(posting_skill_set - resume_skill_set)

    if not posting_skill_set:
        skill_score = 100.0
    else:
        skill_score = round(len(skills_matched) / len(posting_skill_set) * 100, 2)

    if min_years is None:
        experience_match = None
    else:
        experience_match = (resume_years or 0) >= min_years

    overall_score = round(SEMANTIC_WEIGHT * semantic_score + SKILL_WEIGHT * skill_score, 2)

    return ScoreResult(
        overall_score=overall_score,
        semantic_score=semantic_score,
        skill_score=skill_score,
        skills_matched=skills_matched,
        skills_missing=skills_missing,
        experience_match=experience_match,
    )
