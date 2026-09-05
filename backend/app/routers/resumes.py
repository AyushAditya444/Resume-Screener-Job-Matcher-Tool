from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.auth import get_current_user_id
from app.schemas import ResumeCreateRequest, ResumeResponse
from app.services.experience_extraction import extract_education_level, extract_years_of_experience
from app.services.skill_taxonomy import extract_skills
from app.services.text_extraction import extract_text
from app.supabase_client import get_scoped_client

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeResponse, status_code=201)
def create_resume(
    body: ResumeCreateRequest,
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_scoped_client),
):
    file_bytes = client.storage.from_("resumes").download(body.storage_path)

    try:
        text = extract_text(file_bytes, body.original_filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    skills = extract_skills(text)
    years = extract_years_of_experience(text)
    education = extract_education_level(text)

    result = (
        client.table("resumes")
        .insert(
            {
                "user_id": user_id,
                "storage_path": body.storage_path,
                "original_filename": body.original_filename,
                "parsed_text": text,
                "extracted_skills": skills,
                "experience_years": years,
                "education_level": education,
            }
        )
        .execute()
    )
    return result.data[0]


@router.get("", response_model=list[ResumeResponse])
def list_resumes(
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_scoped_client),
):
    result = (
        client.table("resumes")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
