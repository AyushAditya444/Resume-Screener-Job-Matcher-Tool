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
