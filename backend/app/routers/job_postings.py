from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.auth import get_current_user_id
from app.schemas import JobPostingCreateRequest, JobPostingResponse
from app.services.skill_taxonomy import extract_skills
from app.supabase_client import get_scoped_client

router = APIRouter(prefix="/job-postings", tags=["job_postings"])


@router.post("", response_model=JobPostingResponse, status_code=201)
def create_job_posting(
    body: JobPostingCreateRequest,
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_scoped_client),
):
    if not body.raw_text.strip():
        raise HTTPException(status_code=422, detail="Job description text cannot be empty")

    required_skills = extract_skills(body.raw_text)

    result = (
        client.table("job_postings")
        .insert(
            {
                "user_id": user_id,
                "title": body.title,
                "company": body.company,
                "raw_text": body.raw_text,
                "required_skills": required_skills,
                "min_experience_years": body.min_experience_years,
            }
        )
        .execute()
    )
    return result.data[0]


@router.get("", response_model=list[JobPostingResponse])
def list_job_postings(
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_scoped_client),
):
    result = (
        client.table("job_postings")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
