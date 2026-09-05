# Resume Screener / Job-Matcher Tool — Design Spec

**Date:** 2026-09-05
**Status:** Approved for implementation planning

## 1. Overview

A web app that scores how well a resume matches a job description, usable in
two independent modes:

- **Job seeker mode** — a user checks their own resume against a job
  description and sees a match score plus a breakdown of what's missing.
- **Recruiter mode** — a user creates a job posting, uploads multiple
  candidate resumes, and gets them ranked by match score.

This is the third of three portfolio projects being built from the same
resume (after the Phishing E-Mail Detector and the URL Shortener). It should
be a real, working, deployed app — not a notebook or script — and it must run
entirely on free hosting tiers with no paid API dependency.

## 2. Goals / Non-Goals

**Goals:**
- Working end-to-end app: upload → parse → score → explain → persist → revisit.
- Explainable output (matched/missing skills), not just a bare percentage.
- Fully free to run: no paid APIs, free hosting tiers only.
- Clean separation between the two modes while sharing one data model and
  one scoring engine underneath.

**Non-Goals (explicitly out of scope for this version):**
- No LLM-generated natural-language explanations (adds cost; may be a future
  optional add-on, not built now).
- No shared/public job board connecting recruiter postings to job seekers —
  the two modes are independent and private to each account.
- No background job queue / async task processing — batch sizes are kept
  small enough (see §5) to process synchronously within a single request.
- No mobile app, no multi-language support.

## 3. Architecture

```
┌─────────────────┐        REST (JSON, JWT bearer)        ┌──────────────────┐
│  React (Vite)    │ ─────────────────────────────────▶  │  FastAPI backend  │
│  frontend        │ ◀─────────────────────────────────  │  (Render, free)   │
│  (Vercel, free)  │                                       └──────────────────┘
└──────────────────┘                                                │
        │            direct upload (Supabase JS client)             │ parses via
        ▼                                                           │ service key
┌──────────────────────────────────────────────────────────────────▼──────────┐
│                              Supabase (free tier)                            │
│   Auth (email/password login)  │  Postgres (all data)  │  Storage (resumes)  │
└───────────────────────────────────────────────────────────────────────────┘
```

- **Frontend:** React + Vite SPA, deployed on Vercel. Handles login (via
  Supabase's client SDK), both mode UIs, and uploads resume files directly to
  Supabase Storage (bypassing the backend for large file bytes).
- **Backend:** FastAPI, deployed on Render (free web service). Stateless —
  holds no data of its own; every request is authenticated by verifying the
  Supabase-issued JWT on the `Authorization` header. Owns all business logic:
  text extraction, skill/entity extraction, embedding, scoring, persistence.
- **Supabase** provides three services used by this project:
  - **Auth** — email/password signup and login; issues JWTs the frontend
    attaches to API calls and the backend verifies.
  - **Postgres** — all persistent data (see §4).
  - **Storage** — holds the original uploaded resume files (PDF/DOCX). The
    backend fetches a file from Storage (via its service-role key) when it
    needs to parse it.
- **Matching engine** lives inside the FastAPI process as a module. The
  embedding model (`sentence-transformers`) and the spaCy/skill-taxonomy
  pipeline load once at process startup and stay resident in memory. There is
  deliberately no separate ML microservice — unnecessary complexity at this
  scale, and it would only add another free-tier service to keep alive.

## 4. Data Model

All tables live in Supabase Postgres with row-level security enabled so a
user can only read/write their own rows (`user_id = auth.uid()`).

```sql
-- Supabase's built-in auth.users table is used for identity; this holds
-- app-specific profile data.
profiles (
  id            uuid primary key references auth.users(id),
  display_name  text,
  created_at    timestamptz default now()
)

resumes (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid references profiles(id) not null,
  storage_path       text not null,        -- path in Supabase Storage
  original_filename  text not null,
  parsed_text        text,
  extracted_skills   jsonb,                -- e.g. ["python", "sql", ...]
  experience_years   numeric,
  education_level    text,
  created_at         timestamptz default now()
)

job_postings (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid references profiles(id) not null,
  title                 text not null,
  company               text,
  raw_text              text not null,
  required_skills       jsonb,             -- auto-extracted, user-editable
  min_experience_years  numeric,
  created_at            timestamptz default now()
)

screening_results (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid references profiles(id) not null,
  resume_id        uuid references resumes(id) not null,
  job_posting_id   uuid references job_postings(id) not null,
  overall_score    numeric not null,       -- 0-100
  semantic_score   numeric not null,       -- 0-100, embedding similarity
  skill_score      numeric not null,       -- 0-100, skill overlap
  skills_matched   jsonb,
  skills_missing   jsonb,
  experience_match boolean,
  created_at       timestamptz default now()
)
```

Note the key design decision: **one `screening_results` table serves both
modes.** Job seeker mode produces one row (their resume × one posting).
Recruiter mode produces many rows (many resumes × one posting), and the UI
simply queries and sorts by `job_posting_id`. The scoring function and schema
don't need to know which mode triggered them.

## 5. Matching Engine Pipeline

Given one resume and one job posting, scoring proceeds as:

1. **Text extraction** — `pdfplumber`/`PyMuPDF` for PDF resumes, `python-docx`
   for `.docx`. Job descriptions are entered as pasted plain text (no file
   parsing needed on that side).
2. **Structured extraction** — a spaCy pipeline plus a curated skill
   taxonomy (`PhraseMatcher` over a maintained list of tech/soft skills)
   pulls out a skills list from both texts. Regex heuristics extract years
   of experience (e.g. "5+ years") and education level (degree keywords).
3. **Semantic scoring** — both full texts are embedded with a local
   `sentence-transformers` model (`all-MiniLM-L6-v2`); cosine similarity
   between the two vectors gives the semantic score (0–100).
4. **Skill scoring** — the fraction of the job posting's required skills
   present in the resume's extracted skills gives the skill score (0–100).
5. **Overall score** — a fixed weighted combination (60% semantic, 40%
   skill) — simple and good enough for this scale; not user-configurable in
   v1.
6. **Persistence** — the score, its breakdown, matched/missing skill lists,
   and the experience/education fit are written to `screening_results`.

**Batch behavior (recruiter mode):** the same per-resume pipeline runs once
for each uploaded resume against the selected posting. Batch size is capped
at **20 resumes per upload** — enough to produce a meaningful ranked list
without needing a background job queue; each resume takes roughly 1–2
seconds to process, keeping a full batch comfortably inside Render's request
timeout.

## 6. UX Flows

**Job seeker mode:**
1. Log in.
2. Upload a resume (or pick a previously uploaded one).
3. Paste a job description.
4. Click "Check Match" → see overall score, matched skills, missing skills,
   and experience/education fit.
5. Result is saved automatically; a history page lists past checks.

**Recruiter mode:**
1. Log in.
2. Create a job posting (paste text; review/edit the auto-extracted required
   skills before running — builds trust in what's being matched against).
3. Drag-and-drop up to 20 resumes.
4. See a ranked candidates table (sortable by score), each row expandable to
   show that candidate's matched/missing skills.
5. Job postings and their result sets are saved and revisitable from a
   history page.

## 7. Error Handling

- Corrupted or unreadable resume files: reject with a clear inline message
  ("couldn't read this file — is it a valid PDF/DOCX?"), never a crash.
- Empty or too-short job description text: validated client-side and
  server-side before the pipeline runs.
- Batch upload partial failures: one bad file in a batch of 20 is skipped
  and reported by name; the rest of the batch still processes.
- Auth failures (expired/invalid JWT): the API returns 401 and the frontend
  redirects to login.
- Render free-tier cold start: the frontend shows a "waking up the
  server, this can take up to a minute" state on the first request after
  idle — this is expected free-tier behavior, not something to mask or work
  around.
- Startup failure (embedding model or spaCy pipeline fails to load): the
  backend fails fast with a clear log message rather than starting in a
  half-working state; a `/health` endpoint reflects readiness.

## 8. Testing Strategy

- **Unit tests (`pytest`)** for the deterministic parts of the pipeline:
  skill extraction, experience/education regex heuristics, and the score
  combination formula — these are pure functions given fixture resume/JD
  text, so they're cheap to test thoroughly.
- **Integration tests** for the API endpoints using FastAPI's `TestClient`,
  covering the resume-upload → screening → result flow and batch behavior
  (including partial-failure handling).
- **Frontend:** manual QA checklist covering both mode flows end-to-end,
  rather than a full automated test suite — proportionate to a project at
  this scale.

## 9. Deployment

- **Frontend:** Vercel (free), root directory `frontend/`, environment
  variable pointing at the Render backend URL and the Supabase project URL
  and anon key.
- **Backend:** Render (free web service), root directory `backend/`,
  environment variables for the Supabase service-role key, project URL, and
  JWT secret (used to verify tokens issued by Supabase Auth).
- **Database/Auth/Storage:** Supabase (free tier), one project holding
  Postgres, Auth, and a Storage bucket for resumes with row-level security
  policies restricting access to each user's own rows/files.
- No paid services anywhere in this stack; expected trade-offs are Render's
  cold start after 15 minutes idle and Supabase's free-tier storage/row
  limits, both acceptable for a portfolio demo.

## 10. Future Extensions (not built now)

- Optional LLM-generated natural-language "why you match" explanation,
  gated behind a user action so cost stays opt-in and minimal.
- Connected/public mode where recruiter postings are browsable by job
  seekers (a real job-board feature — meaningfully more scope).
- Configurable scoring weights (semantic vs. skill) exposed to the user.
