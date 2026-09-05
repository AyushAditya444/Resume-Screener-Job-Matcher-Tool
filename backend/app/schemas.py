from pydantic import BaseModel


class ResumeCreateRequest(BaseModel):
    storage_path: str
    original_filename: str


class ResumeResponse(BaseModel):
    id: str
    storage_path: str
    original_filename: str
    parsed_text: str
    extracted_skills: list[str]
    experience_years: float | None
    education_level: str | None
    created_at: str


class JobPostingCreateRequest(BaseModel):
    title: str
    company: str | None = None
    raw_text: str
    min_experience_years: float | None = None


class JobPostingResponse(BaseModel):
    id: str
    title: str
    company: str | None
    raw_text: str
    required_skills: list[str]
    min_experience_years: float | None
    created_at: str


class ScreeningRequest(BaseModel):
    resume_ids: list[str]
    job_posting_id: str

    def validate_batch_size(self) -> None:
        if len(self.resume_ids) == 0:
            raise ValueError("At least one resume_id is required")
        if len(self.resume_ids) > 20:
            raise ValueError("A maximum of 20 resumes can be screened per request")


class ScreeningResultResponse(BaseModel):
    resume_id: str
    error: str | None = None
    id: str | None = None
    overall_score: float | None = None
    semantic_score: float | None = None
    skill_score: float | None = None
    skills_matched: list[str] | None = None
    skills_missing: list[str] | None = None
    experience_match: bool | None = None
    created_at: str | None = None
