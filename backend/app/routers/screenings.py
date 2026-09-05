from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client

from app.auth import get_current_user_id
from app.schemas import ScreeningRequest, ScreeningResultResponse
from app.services.scoring import score_resume_against_posting
from app.supabase_client import get_scoped_client

router = APIRouter(prefix="/screenings", tags=["screenings"])


@router.post("", response_model=list[ScreeningResultResponse], status_code=201)
def create_screenings(
    body: ScreeningRequest,
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_scoped_client),
):
    try:
        body.validate_batch_size()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    posting = (
        client.table("job_postings")
        .select("*")
        .eq("id", body.job_posting_id)
        .single()
        .execute()
        .data
    )

    resumes = (
        client.table("resumes")
        .select("*")
        .eq("user_id", user_id)
        .in_("id", body.resume_ids)
        .execute()
        .data
    )
    resumes_by_id = {r["id"]: r for r in resumes}

    results = []
    for resume_id in body.resume_ids:
        resume = resumes_by_id.get(resume_id)
        if resume is None:
            results.append(ScreeningResultResponse(resume_id=resume_id, error="Resume not found"))
            continue
        try:
            score = score_resume_against_posting(
                resume_text=resume["parsed_text"],
                resume_skills=resume["extracted_skills"],
                resume_years=resume["experience_years"],
                posting_text=posting["raw_text"],
                posting_skills=posting["required_skills"],
                min_years=posting["min_experience_years"],
            )
        except Exception as exc:
            results.append(ScreeningResultResponse(resume_id=resume_id, error=str(exc)))
            continue

        saved = (
            client.table("screening_results")
            .insert(
                {
                    "user_id": user_id,
                    "resume_id": resume_id,
                    "job_posting_id": body.job_posting_id,
                    "overall_score": score.overall_score,
                    "semantic_score": score.semantic_score,
                    "skill_score": score.skill_score,
                    "skills_matched": score.skills_matched,
                    "skills_missing": score.skills_missing,
                    "experience_match": score.experience_match,
                }
            )
            .execute()
            .data[0]
        )
        results.append(ScreeningResultResponse(**saved))

    return results


@router.get("", response_model=list[ScreeningResultResponse])
def list_screenings(
    job_posting_id: str | None = Query(default=None),
    resume_id: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_scoped_client),
):
    query = client.table("screening_results").select("*").eq("user_id", user_id)
    if job_posting_id:
        query = query.eq("job_posting_id", job_posting_id)
    if resume_id:
        query = query.eq("resume_id", resume_id)
    result = query.order("overall_score", desc=True).execute()
    return [ScreeningResultResponse(**row) for row in result.data]
