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
