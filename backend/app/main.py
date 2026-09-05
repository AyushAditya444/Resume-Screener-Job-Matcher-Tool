import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import job_postings, resumes, screenings
from app.services.embeddings import get_embedding_model

logger = logging.getLogger("uvicorn.error")

_model_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model_ready
    get_embedding_model()  # raises and fails startup if the model can't load
    _model_ready = True
    yield


app = FastAPI(title="Resume Screener / Job-Matcher API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Starlette's outermost error-handling layer sits above CORSMiddleware,
    # so an exception that escapes here entirely would produce a response
    # with no CORS headers at all - the browser reports that as a CORS
    # failure, masking the real (server-side) error. Catching it here keeps
    # the response inside CORSMiddleware's reach and still logs the traceback.
    logger.exception("Unhandled exception during request")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok" if _model_ready else "starting"}


app.include_router(resumes.router)
app.include_router(job_postings.router)
app.include_router(screenings.router)
