from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.embeddings import get_embedding_model

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


@app.get("/health")
def health():
    return {"status": "ok" if _model_ready else "starting"}
