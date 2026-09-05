# Resume Screener / Job-Matcher Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a working web app that scores resumes against job descriptions in two independent modes (job seeker, recruiter), fully on free hosting.

**Architecture:** React (Vite) SPA on Vercel talks to a stateless FastAPI backend on Render over REST, authenticated with Supabase-issued JWTs. Supabase provides Auth, Postgres, and Storage. The matching engine (text extraction → skill/entity extraction → embedding similarity → weighted score) lives inside the FastAPI process as a module, loaded once at startup.

**Tech Stack:** Python 3.11 / FastAPI / pydantic v2 / supabase-py / spaCy (blank tokenizer + PhraseMatcher, no pretrained model) / sentence-transformers (`all-MiniLM-L6-v2`) / pdfplumber / python-docx / pytest — React 18 / Vite / TypeScript / @supabase/supabase-js — Postgres via Supabase.

**Spec:** `docs/superpowers/specs/2026-09-05-resume-screener-job-matcher-design.md`

## Global Constraints

- No paid APIs anywhere in the app (spec §2) — matching runs entirely on local/open-source models.
- Backend is stateless; all persistent state lives in Supabase (spec §3).
- Row-level security on every Supabase table restricts each user to their own rows (spec §4) — the backend must act as the requesting user (via their JWT), never as an unrestricted service role, for any read/write of user data.
- Batch resume uploads are capped at 20 files per request (spec §5) — no background job queue.
- Overall score = 60% semantic similarity + 40% skill overlap, fixed (not user-configurable) (spec §5).
- One `screening_results` table serves both job-seeker and recruiter modes — do not create separate tables per mode (spec §4).
- Job seeker mode and recruiter mode are fully independent/private per account — no shared/public postings (spec §2 non-goals).
- Frontend testing is manual QA, not an automated suite (spec §8) — frontend tasks below use manual verification steps instead of automated test runs; backend logic is TDD throughout.

---

## Phase 1: Project Scaffolding

### Task 1: Backend skeleton with health check

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.config.Settings` (pydantic-settings class with fields `supabase_url: str`, `supabase_anon_key: str`, `supabase_jwt_secret: str`, `cors_origins: list[str]`), `app.main.app` (the FastAPI instance), `GET /health` returning `{"status": "ok"}`.

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.0
supabase==2.9.0
pyjwt==2.9.0
pdfplumber==0.11.4
python-docx==1.1.2
spacy==3.8.2
sentence-transformers==3.2.1
pytest==8.3.3
httpx==0.27.2
python-multipart==0.0.12
```

- [ ] **Step 2: Write `app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_jwt_secret: str
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 3: Write the failing test**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: FAIL (`app.main` does not exist yet)

- [ ] **Step 5: Write `app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Resume Screener / Job-Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create a `.env` for local testing**

```
# backend/.env
SUPABASE_URL=http://localhost
SUPABASE_ANON_KEY=test-anon-key
SUPABASE_JWT_SECRET=test-jwt-secret
CORS_ORIGINS=["http://localhost:5173"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/requirements.txt backend/app backend/tests/test_health.py backend/.env
git commit -m "feat(backend): scaffold FastAPI app with health check"
```

---

### Task 2: Database schema and row-level security

**Files:**
- Create: `supabase/migrations/0001_init.sql`

**Interfaces:**
- Produces: tables `profiles`, `resumes`, `job_postings`, `screening_results` exactly as defined in spec §4, each with RLS enabled and an owner-only policy.

- [ ] **Step 1: Write the migration**

```sql
-- supabase/migrations/0001_init.sql

create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

create table resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  storage_path text not null,
  original_filename text not null,
  parsed_text text,
  extracted_skills jsonb,
  experience_years numeric,
  education_level text,
  created_at timestamptz not null default now()
);

create table job_postings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  title text not null,
  company text,
  raw_text text not null,
  required_skills jsonb,
  min_experience_years numeric,
  created_at timestamptz not null default now()
);

create table screening_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  resume_id uuid not null references resumes(id) on delete cascade,
  job_posting_id uuid not null references job_postings(id) on delete cascade,
  overall_score numeric not null,
  semantic_score numeric not null,
  skill_score numeric not null,
  skills_matched jsonb,
  skills_missing jsonb,
  experience_match boolean,
  created_at timestamptz not null default now()
);

alter table profiles enable row level security;
alter table resumes enable row level security;
alter table job_postings enable row level security;
alter table screening_results enable row level security;

create policy "own profile" on profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

create policy "own resumes" on resumes
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own job postings" on job_postings
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own screening results" on screening_results
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Storage bucket for resume files, owner-only access.
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;

create policy "own resume files read" on storage.objects
  for select using (bucket_id = 'resumes' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "own resume files write" on storage.objects
  for insert with check (bucket_id = 'resumes' and auth.uid()::text = (storage.foldername(name))[1]);

create policy "own resume files delete" on storage.objects
  for delete using (bucket_id = 'resumes' and auth.uid()::text = (storage.foldername(name))[1]);
```

- [ ] **Step 2: Apply the migration**

Run this in the Supabase project's SQL Editor (or via `supabase db push` if the Supabase CLI is linked to the project).
Expected: four tables created, RLS enabled, `resumes` storage bucket created.

- [ ] **Step 3: Verify RLS is working**

In the Supabase Table Editor, confirm each of the four tables shows "RLS enabled" and lists the policy just created. This is a manual check — there is no automated test for a fresh Supabase project's policies at this stage; API-level tests in later tasks will exercise these policies indirectly.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/0001_init.sql
git commit -m "feat(db): add schema and RLS policies for profiles, resumes, job_postings, screening_results"
```

---

### Task 3: Frontend skeleton

**Files:**
- Create: `frontend/` (via Vite scaffold)
- Create: `frontend/src/lib/supabaseClient.ts`
- Create: `frontend/.env.example`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Produces: `frontend/src/lib/supabaseClient.ts` exporting `supabase` (a configured `SupabaseClient`), a routed `App.tsx` with placeholder routes `/login`, `/job-seeker`, `/recruiter`.

- [ ] **Step 1: Scaffold the Vite project**

Run: `npm create vite@latest frontend -- --template react-ts`
Then: `cd frontend && npm install && npm install @supabase/supabase-js react-router-dom`

- [ ] **Step 2: Write `.env.example`**

```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_URL=http://localhost:8000
```

Copy it to `.env.local` with real values before running locally.

- [ ] **Step 3: Write `src/lib/supabaseClient.ts`**

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

- [ ] **Step 4: Set up routing in `src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

function Placeholder({ label }: { label: string }) {
  return <div>{label}</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Placeholder label="Login" />} />
        <Route path="/job-seeker" element={<Placeholder label="Job Seeker" />} />
        <Route path="/recruiter" element={<Placeholder label="Recruiter" />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 5: Manually verify**

Run: `npm run dev`
Expected: visiting `http://localhost:5173` redirects to `/login` and shows "Login"; visiting `/job-seeker` and `/recruiter` shows the corresponding placeholder text.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): scaffold Vite React app with routing and Supabase client"
```

---

## Phase 2: Authentication

### Task 4: Backend JWT verification dependency

**Files:**
- Create: `backend/app/auth.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `app.config.settings.supabase_jwt_secret`
- Produces: `app.auth.get_current_user_id(authorization: str = Header(...)) -> str`, a FastAPI dependency that returns the authenticated user's UUID or raises `HTTPException(401)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_auth.py
import jwt
import pytest
from fastapi import HTTPException

from app.auth import decode_user_id
from app.config import settings


def test_decode_user_id_from_valid_token():
    token = jwt.encode(
        {"sub": "11111111-1111-1111-1111-111111111111", "aud": "authenticated"},
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    assert decode_user_id(token) == "11111111-1111-1111-1111-111111111111"


def test_decode_user_id_rejects_bad_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_user_id("not-a-real-token")
    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: FAIL (`app.auth` does not exist)

- [ ] **Step 3: Write `app/auth.py`**

```python
import jwt
from fastapi import Header, HTTPException

from app.config import settings


def decode_user_id(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    return payload["sub"]


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    return decode_user_id(token)


def get_bearer_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth.py backend/tests/test_auth.py
git commit -m "feat(backend): add Supabase JWT verification dependency"
```

---

### Task 5: Supabase client scoped to the requesting user

**Files:**
- Create: `backend/app/supabase_client.py`
- Test: `backend/tests/test_supabase_client.py`

**Interfaces:**
- Consumes: `app.auth.get_bearer_token`
- Produces: `app.supabase_client.get_scoped_client(token: str = Depends(get_bearer_token)) -> Client`, a `supabase-py` client whose PostgREST and Storage calls are authenticated as the requesting user (so RLS policies from Task 2 apply automatically — the backend never uses a service-role key for user data).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_supabase_client.py
from unittest.mock import patch

from app.supabase_client import get_scoped_client


def test_scoped_client_sets_auth_token():
    with patch("app.supabase_client.create_client") as mock_create:
        mock_client = mock_create.return_value
        result = get_scoped_client(token="user-jwt-123")
        mock_client.postgrest.auth.assert_called_once_with("user-jwt-123")
        mock_client.storage.session.headers.update.assert_called_once_with(
            {"Authorization": "Bearer user-jwt-123"}
        )
        assert result is mock_client
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_supabase_client.py -v`
Expected: FAIL (`app.supabase_client` does not exist)

- [ ] **Step 3: Write `app/supabase_client.py`**

```python
from fastapi import Depends
from supabase import Client, create_client

from app.auth import get_bearer_token
from app.config import settings


def get_scoped_client(token: str = Depends(get_bearer_token)) -> Client:
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(token)
    client.storage.session.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_supabase_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/supabase_client.py backend/tests/test_supabase_client.py
git commit -m "feat(backend): add user-scoped Supabase client so RLS applies to every request"
```

---

### Task 6: Frontend auth (signup, login, session context)

**Files:**
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/SignupPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `frontend/src/lib/supabaseClient.ts` → `supabase`
- Produces: `useAuth()` hook returning `{ session, signUp, signIn, signOut }`; a `RequireAuth` wrapper component used by protected routes.

- [ ] **Step 1: Write `src/context/AuthContext.tsx`**

```tsx
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';

interface AuthContextValue {
  session: Session | null;
  loading: boolean;
  signUp: (email: string, password: string) => Promise<{ error: string | null }>;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function signUp(email: string, password: string) {
    const { error } = await supabase.auth.signUp({ email, password });
    return { error: error?.message ?? null };
  }

  async function signIn(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error: error?.message ?? null };
  }

  async function signOut() {
    await supabase.auth.signOut();
  }

  return (
    <AuthContext.Provider value={{ session, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
```

- [ ] **Step 2: Write `src/pages/LoginPage.tsx`**

```tsx
import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const { error } = await signIn(email, password);
    if (error) {
      setError(error);
      return;
    }
    navigate('/job-seeker');
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Log in</h1>
      {error && <p role="alert">{error}</p>}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button type="submit">Log in</button>
      <p>No account? <Link to="/signup">Sign up</Link></p>
    </form>
  );
}
```

- [ ] **Step 3: Write `src/pages/SignupPage.tsx`**

```tsx
import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function SignupPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const { error } = await signUp(email, password);
    if (error) {
      setError(error);
      return;
    }
    navigate('/job-seeker');
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Sign up</h1>
      {error && <p role="alert">{error}</p>}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <button type="submit">Sign up</button>
      <p>Already have an account? <Link to="/login">Log in</Link></p>
    </form>
  );
}
```

- [ ] **Step 4: Add a `RequireAuth` guard and wire routes in `src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';

function RequireAuth({ children }: { children: JSX.Element }) {
  const { session, loading } = useAuth();
  if (loading) return <p>Loading...</p>;
  if (!session) return <Navigate to="/login" replace />;
  return children;
}

function Placeholder({ label }: { label: string }) {
  return <div>{label}</div>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/job-seeker"
            element={<RequireAuth><Placeholder label="Job Seeker" /></RequireAuth>}
          />
          <Route
            path="/recruiter"
            element={<RequireAuth><Placeholder label="Recruiter" /></RequireAuth>}
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

- [ ] **Step 5: Manually verify**

Run: `npm run dev`. Sign up with a test email/password (check Supabase Auth settings — disable "confirm email" for local testing, or check the inbox). Confirm: after signup you land on `/job-seeker`; after signing out and visiting `/job-seeker` directly, you're redirected to `/login`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): add signup, login, and route protection via Supabase Auth"
```

---

## Phase 3: Matching Engine

### Task 7: Resume text extraction

**Files:**
- Create: `backend/app/services/text_extraction.py`
- Test: `backend/tests/test_text_extraction.py`
- Test fixtures: `backend/tests/fixtures/sample_resume.pdf`, `backend/tests/fixtures/sample_resume.docx`

**Interfaces:**
- Produces: `extract_text(file_bytes: bytes, filename: str) -> str`, raising `ValueError` for unsupported/corrupt files.

- [ ] **Step 1: Create fixture files**

Create `backend/tests/fixtures/sample_resume.docx` containing the single paragraph "Jane Doe. Software Engineer with 5 years of experience in Python, SQL, and React. B.S. in Computer Science."
Create `backend/tests/fixtures/sample_resume.pdf` with the same text (e.g. by printing that paragraph to PDF from any editor, or generating it with `reportlab` in a throwaway script — the fixture just needs to be a valid, text-extractable PDF).

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_text_extraction.py
import pytest
from pathlib import Path

from app.services.text_extraction import extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_extracts_text_from_docx():
    data = (FIXTURES / "sample_resume.docx").read_bytes()
    text = extract_text(data, "sample_resume.docx")
    assert "Python" in text
    assert "5 years" in text


def test_extracts_text_from_pdf():
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    text = extract_text(data, "sample_resume.pdf")
    assert "Python" in text


def test_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(b"whatever", "resume.txt")


def test_rejects_corrupt_pdf():
    with pytest.raises(ValueError, match="Could not read"):
        extract_text(b"not a real pdf", "resume.pdf")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_text_extraction.py -v`
Expected: FAIL (`app.services.text_extraction` does not exist)

- [ ] **Step 4: Write `app/services/text_extraction.py`**

```python
import io

import pdfplumber
from docx import Document


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if lower_name.endswith(".docx"):
        return _extract_docx(file_bytes)
    raise ValueError(f"Unsupported file type: {filename}")


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
    except Exception as exc:
        raise ValueError("Could not read PDF file") from exc
    if not text:
        raise ValueError("Could not read PDF file: no extractable text")
    return text


def _extract_docx(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in document.paragraphs).strip()
    except Exception as exc:
        raise ValueError("Could not read DOCX file") from exc
    if not text:
        raise ValueError("Could not read DOCX file: no extractable text")
    return text
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_text_extraction.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/text_extraction.py backend/tests/test_text_extraction.py backend/tests/fixtures
git commit -m "feat(backend): add PDF/DOCX text extraction with corrupt-file handling"
```

---

### Task 8: Skill taxonomy extraction

**Files:**
- Create: `backend/app/services/skill_taxonomy.py`
- Test: `backend/tests/test_skill_taxonomy.py`

**Interfaces:**
- Consumes: `spacy` (blank English tokenizer only — no pretrained model download required)
- Produces: `extract_skills(text: str) -> list[str]`, returning lower-cased, de-duplicated matched skills from a fixed taxonomy list.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_skill_taxonomy.py
from app.services.skill_taxonomy import extract_skills


def test_extracts_known_skills_case_insensitively():
    text = "Experienced in Python, SQL and React. Familiar with docker and Kubernetes."
    skills = extract_skills(text)
    assert set(skills) == {"python", "sql", "react", "docker", "kubernetes"}


def test_ignores_unknown_terms():
    text = "Skilled in Python and the ancient art of underwater basket weaving."
    skills = extract_skills(text)
    assert skills == ["python"]


def test_deduplicates_repeated_mentions():
    text = "Python developer. Also did Python scripting and more Python work."
    skills = extract_skills(text)
    assert skills == ["python"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_skill_taxonomy.py -v`
Expected: FAIL (`app.services.skill_taxonomy` does not exist)

- [ ] **Step 3: Write `app/services/skill_taxonomy.py`**

```python
import spacy
from spacy.matcher import PhraseMatcher

# A starter taxonomy — extend this list over time as real resumes/postings
# surface skills it misses. Kept as plain lowercase strings; multi-word
# skills are matched as phrases.
SKILL_TAXONOMY = [
    "python", "java", "javascript", "typescript", "sql", "nosql", "react",
    "vue", "angular", "node.js", "fastapi", "django", "flask", "docker",
    "kubernetes", "aws", "azure", "gcp", "git", "linux", "html", "css",
    "machine learning", "deep learning", "nlp", "pandas", "numpy",
    "scikit-learn", "pytorch", "tensorflow", "postgresql", "mysql",
    "mongodb", "redis", "graphql", "rest api", "ci/cd", "terraform",
    "communication", "leadership", "project management", "agile", "scrum",
]

_nlp = spacy.blank("en")
_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_matcher.add("SKILLS", [_nlp.make_doc(skill) for skill in SKILL_TAXONOMY])


def extract_skills(text: str) -> list[str]:
    doc = _nlp.make_doc(text)
    matches = _matcher(doc)
    found = []
    seen = set()
    for match_id, start, end in matches:
        skill = doc[start:end].text.lower()
        if skill not in seen:
            seen.add(skill)
            found.append(skill)
    return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_skill_taxonomy.py -v`
Expected: PASS

Note: this uses `spacy.blank("en")` with only the tokenizer, not a
pretrained model, so no model download is required anywhere in this
project — Task 9 (experience/education extraction) uses plain regex
rather than spaCy NER, which is sufficient for the patterns needed here.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/skill_taxonomy.py backend/tests/test_skill_taxonomy.py
git commit -m "feat(backend): add phrase-matcher-based skill extraction"
```

---

### Task 9: Experience and education extraction

**Files:**
- Create: `backend/app/services/experience_extraction.py`
- Test: `backend/tests/test_experience_extraction.py`

**Interfaces:**
- Produces: `extract_years_of_experience(text: str) -> float | None`, `extract_education_level(text: str) -> str | None` (one of `"high_school"`, `"associate"`, `"bachelor"`, `"master"`, `"doctorate"`, or `None`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_experience_extraction.py
from app.services.experience_extraction import (
    extract_years_of_experience,
    extract_education_level,
)


def test_extracts_plus_years():
    assert extract_years_of_experience("5+ years of experience in backend development") == 5.0


def test_extracts_plain_years():
    assert extract_years_of_experience("3 years of experience with React") == 3.0


def test_returns_none_when_no_years_mentioned():
    assert extract_years_of_experience("Skilled Python developer") is None


def test_extracts_bachelor_degree():
    assert extract_education_level("B.S. in Computer Science, State University") == "bachelor"


def test_extracts_master_degree():
    assert extract_education_level("Completed an M.S. in Data Science") == "master"


def test_extracts_doctorate():
    assert extract_education_level("Ph.D. in Information Science") == "doctorate"


def test_returns_none_when_no_degree_mentioned():
    assert extract_education_level("Self-taught developer, no formal degree") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_experience_extraction.py -v`
Expected: FAIL (`app.services.experience_extraction` does not exist)

- [ ] **Step 3: Write `app/services/experience_extraction.py`**

```python
import re

_YEARS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", re.IGNORECASE)

_EDUCATION_PATTERNS = [
    ("doctorate", re.compile(r"\bph\.?d\.?\b|\bdoctorate\b", re.IGNORECASE)),
    ("master", re.compile(r"\bm\.?s\.?\b|\bmaster'?s?\b|\bmba\b", re.IGNORECASE)),
    ("bachelor", re.compile(r"\bb\.?s\.?\b|\bb\.?a\.?\b|\bbachelor'?s?\b", re.IGNORECASE)),
    ("associate", re.compile(r"\bassociate'?s?\b", re.IGNORECASE)),
    ("high_school", re.compile(r"\bhigh school\b|\bg\.?e\.?d\.?\b", re.IGNORECASE)),
]

# Highest degree wins if multiple are mentioned.
_EDUCATION_RANK = ["high_school", "associate", "bachelor", "master", "doctorate"]


def extract_years_of_experience(text: str) -> float | None:
    match = _YEARS_PATTERN.search(text)
    if not match:
        return None
    return float(match.group(1))


def extract_education_level(text: str) -> str | None:
    found = [level for level, pattern in _EDUCATION_PATTERNS if pattern.search(text)]
    if not found:
        return None
    return max(found, key=_EDUCATION_RANK.index)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_experience_extraction.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/experience_extraction.py backend/tests/test_experience_extraction.py
git commit -m "feat(backend): add regex-based years-of-experience and education extraction"
```

---

### Task 10: Semantic embedding similarity

**Files:**
- Create: `backend/app/services/embeddings.py`
- Test: `backend/tests/test_embeddings.py`

**Interfaces:**
- Produces: `get_embedding_model()` (loads and caches the model once), `semantic_similarity(text_a: str, text_b: str) -> float` returning a 0–100 score.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_embeddings.py
from app.services.embeddings import semantic_similarity


def test_similar_texts_score_highly():
    score = semantic_similarity(
        "Experienced Python backend engineer skilled in FastAPI and SQL",
        "Looking for a backend developer with Python and SQL experience",
    )
    assert score > 60


def test_dissimilar_texts_score_lower():
    score = semantic_similarity(
        "Experienced Python backend engineer skilled in FastAPI and SQL",
        "Seeking a pastry chef with 5 years of experience in French baking",
    )
    assert score < 40


def test_score_is_bounded_0_to_100():
    score = semantic_similarity("some text", "some text")
    assert 0 <= score <= 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_embeddings.py -v`
Expected: FAIL (`app.services.embeddings` does not exist)

- [ ] **Step 3: Write `app/services/embeddings.py`**

```python
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def semantic_similarity(text_a: str, text_b: str) -> float:
    model = get_embedding_model()
    embeddings = model.encode([text_a, text_b])
    a, b = embeddings[0], embeddings[1]
    cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    # Cosine similarity for sentence embeddings is typically in [-1, 1]
    # but rarely negative for real text; clamp and rescale to 0-100.
    cosine = max(-1.0, min(1.0, cosine))
    return round((cosine + 1) / 2 * 100, 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_embeddings.py -v`
Expected: PASS (first run downloads the ~80MB model — allow extra time)

- [ ] **Step 5: Load the model eagerly at startup and expose readiness on `/health`**

Per spec §3, the embedding model should load once at process startup and stay resident, not lazily on the first request — so a cold instance is ready before it serves traffic, and a model-load failure is caught immediately rather than surfacing on someone's first request.

```python
# Modify backend/app/main.py

from contextlib import asynccontextmanager

from app.services.embeddings import get_embedding_model

_model_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model_ready
    get_embedding_model()  # raises and fails startup if the model can't load
    _model_ready = True
    yield


app = FastAPI(title="Resume Screener / Job-Matcher API", lifespan=lifespan)

# ... (CORS middleware setup stays as-is) ...


@app.get("/health")
def health():
    return {"status": "ok" if _model_ready else "starting"}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/embeddings.py backend/tests/test_embeddings.py backend/app/main.py
git commit -m "feat(backend): add sentence-transformer semantic similarity scoring, load model at startup"
```

---

### Task 11: Score combination

**Files:**
- Create: `backend/app/services/scoring.py`
- Test: `backend/tests/test_scoring.py`

**Interfaces:**
- Consumes: `extract_skills` (Task 8), `extract_years_of_experience` (Task 9), `semantic_similarity` (Task 10)
- Produces: `score_resume_against_posting(resume_text: str, resume_skills: list[str], resume_years: float | None, posting_text: str, posting_skills: list[str], min_years: float | None) -> ScoreResult`, where `ScoreResult` is a dataclass with fields `overall_score: float`, `semantic_score: float`, `skill_score: float`, `skills_matched: list[str]`, `skills_missing: list[str]`, `experience_match: bool | None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_scoring.py
from unittest.mock import patch

from app.services.scoring import score_resume_against_posting


def test_full_skill_overlap_and_experience_met():
    with patch("app.services.scoring.semantic_similarity", return_value=80.0):
        result = score_resume_against_posting(
            resume_text="...",
            resume_skills=["python", "sql", "react"],
            resume_years=5.0,
            posting_text="...",
            posting_skills=["python", "sql"],
            min_years=3.0,
        )
    assert result.skill_score == 100.0
    assert result.semantic_score == 80.0
    assert result.overall_score == round(0.6 * 80.0 + 0.4 * 100.0, 2)
    assert set(result.skills_matched) == {"python", "sql"}
    assert result.skills_missing == []
    assert result.experience_match is True


def test_partial_skill_overlap_and_experience_not_met():
    with patch("app.services.scoring.semantic_similarity", return_value=50.0):
        result = score_resume_against_posting(
            resume_text="...",
            resume_skills=["python"],
            resume_years=1.0,
            posting_text="...",
            posting_skills=["python", "sql", "docker"],
            min_years=3.0,
        )
    assert result.skill_score == round(1 / 3 * 100, 2)
    assert set(result.skills_matched) == {"python"}
    assert set(result.skills_missing) == {"sql", "docker"}
    assert result.experience_match is False


def test_no_required_skills_gives_full_skill_score():
    with patch("app.services.scoring.semantic_similarity", return_value=70.0):
        result = score_resume_against_posting(
            resume_text="...",
            resume_skills=["python"],
            resume_years=None,
            posting_text="...",
            posting_skills=[],
            min_years=None,
        )
    assert result.skill_score == 100.0
    assert result.experience_match is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_scoring.py -v`
Expected: FAIL (`app.services.scoring` does not exist)

- [ ] **Step 3: Write `app/services/scoring.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_scoring.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat(backend): combine semantic and skill scores into overall match result"
```

---

## Phase 4: API Endpoints

### Task 12: Resume upload and processing endpoint

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/routers/resumes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_resumes_api.py`

**Interfaces:**
- Consumes: `get_current_user_id` (Task 4), `get_scoped_client` (Task 5), `extract_text` (Task 7), `extract_skills` (Task 8), `extract_years_of_experience`/`extract_education_level` (Task 9)
- Produces: `POST /resumes` (body: `{storage_path, original_filename}`, returns the created resume row including extracted fields), `GET /resumes` (returns the user's resumes, newest first).

- [ ] **Step 1: Write `app/schemas.py`**

```python
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
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_resumes_api.py
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth_headers():
    return {"Authorization": "Bearer fake-token"}


@patch("app.routers.resumes.extract_education_level", return_value="bachelor")
@patch("app.routers.resumes.extract_years_of_experience", return_value=5.0)
@patch("app.routers.resumes.extract_skills", return_value=["python", "sql"])
@patch("app.routers.resumes.extract_text", return_value="Jane Doe resume text")
@patch("app.routers.resumes.get_scoped_client")
@patch("app.routers.resumes.get_current_user_id", return_value="user-1")
def test_create_resume_downloads_parses_and_stores(
    mock_user, mock_client_dep, mock_extract_text, mock_extract_skills,
    mock_years, mock_education,
):
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.download.return_value = b"file-bytes"
    inserted_row = {
        "id": "resume-1",
        "storage_path": "user-1/resume.pdf",
        "original_filename": "resume.pdf",
        "parsed_text": "Jane Doe resume text",
        "extracted_skills": ["python", "sql"],
        "experience_years": 5.0,
        "education_level": "bachelor",
        "created_at": "2026-09-05T00:00:00Z",
    }
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [inserted_row]
    mock_client_dep.return_value = mock_client

    response = client.post(
        "/resumes",
        json={"storage_path": "user-1/resume.pdf", "original_filename": "resume.pdf"},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["extracted_skills"] == ["python", "sql"]
    assert body["experience_years"] == 5.0


@patch("app.routers.resumes.extract_text", side_effect=ValueError("Could not read PDF file"))
@patch("app.routers.resumes.get_scoped_client")
@patch("app.routers.resumes.get_current_user_id", return_value="user-1")
def test_create_resume_returns_422_for_unreadable_file(mock_user, mock_client_dep, mock_extract_text):
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.download.return_value = b"garbage"
    mock_client_dep.return_value = mock_client

    response = client.post(
        "/resumes",
        json={"storage_path": "user-1/bad.pdf", "original_filename": "bad.pdf"},
        headers=_auth_headers(),
    )

    assert response.status_code == 422
    assert "Could not read PDF file" in response.json()["detail"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_resumes_api.py -v`
Expected: FAIL (`app.routers.resumes` does not exist)

- [ ] **Step 4: Write `app/routers/resumes.py`**

```python
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
```

- [ ] **Step 5: Register the router in `app/main.py`**

```python
# Add to backend/app/main.py, after the existing imports:
from app.routers import resumes

# Add after the /health route:
app.include_router(resumes.router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_resumes_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/resumes.py backend/app/main.py backend/tests/test_resumes_api.py
git commit -m "feat(backend): add resume upload/list endpoints with parsing pipeline"
```

---

### Task 13: Job posting endpoint

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/routers/job_postings.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_job_postings_api.py`

**Interfaces:**
- Produces: `POST /job-postings` (body: `{title, company, raw_text, min_experience_years}`, auto-extracts `required_skills` from `raw_text`, returns the created row), `GET /job-postings`.

- [ ] **Step 1: Add schemas to `app/schemas.py`**

```python
# Append to backend/app/schemas.py

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
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_job_postings_api.py
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.routers.job_postings.extract_skills", return_value=["python", "docker"])
@patch("app.routers.job_postings.get_scoped_client")
@patch("app.routers.job_postings.get_current_user_id", return_value="user-1")
def test_create_job_posting_extracts_required_skills(mock_user, mock_client_dep, mock_extract):
    mock_client = MagicMock()
    inserted_row = {
        "id": "posting-1",
        "title": "Backend Engineer",
        "company": "Acme",
        "raw_text": "Need Python and Docker experience",
        "required_skills": ["python", "docker"],
        "min_experience_years": 3.0,
        "created_at": "2026-09-05T00:00:00Z",
    }
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [inserted_row]
    mock_client_dep.return_value = mock_client

    response = client.post(
        "/job-postings",
        json={
            "title": "Backend Engineer",
            "company": "Acme",
            "raw_text": "Need Python and Docker experience",
            "min_experience_years": 3.0,
        },
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 201
    assert response.json()["required_skills"] == ["python", "docker"]


@patch("app.routers.job_postings.get_scoped_client")
@patch("app.routers.job_postings.get_current_user_id", return_value="user-1")
def test_create_job_posting_rejects_empty_text(mock_user, mock_client_dep):
    response = client.post(
        "/job-postings",
        json={"title": "Backend Engineer", "raw_text": "   "},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_job_postings_api.py -v`
Expected: FAIL (`app.routers.job_postings` does not exist)

- [ ] **Step 4: Write `app/routers/job_postings.py`**

```python
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
```

- [ ] **Step 5: Register the router in `app/main.py`**

```python
# Add to backend/app/main.py, after the resumes import:
from app.routers import job_postings

# Add after app.include_router(resumes.router):
app.include_router(job_postings.router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_job_postings_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/job_postings.py backend/app/main.py backend/tests/test_job_postings_api.py
git commit -m "feat(backend): add job posting endpoint with auto-extracted required skills"
```

---

### Task 14: Screening endpoint (single and batch)

**Files:**
- Modify: `backend/app/schemas.py`
- Create: `backend/app/routers/screenings.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_screenings_api.py`

**Interfaces:**
- Consumes: `score_resume_against_posting` (Task 11)
- Produces: `POST /screenings` (body: `{resume_ids: list[str], job_posting_id: str}`, max 20 `resume_ids`; scores each resume against the posting, persists a `screening_results` row per resume, returns the list of results — failures for individual resumes are reported per-item rather than failing the whole batch), `GET /screenings?job_posting_id=...` (ranked results for a posting) and `GET /screenings?resume_id=...` (a job seeker's own results).

- [ ] **Step 1: Add schemas to `app/schemas.py`**

```python
# Append to backend/app/schemas.py

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
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_screenings_api.py
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.scoring import ScoreResult

client = TestClient(app)


def _mock_client_with_data(resumes, posting):
    mock_client = MagicMock()

    def table_side_effect(name):
        table_mock = MagicMock()
        if name == "resumes":
            table_mock.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = resumes
        elif name == "job_postings":
            table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value.data = posting
        elif name == "screening_results":
            table_mock.insert.return_value.execute.return_value.data = [
                {
                    "id": "result-1",
                    "resume_id": resumes[0]["id"] if resumes else None,
                    "overall_score": 88.0,
                    "semantic_score": 80.0,
                    "skill_score": 100.0,
                    "skills_matched": ["python"],
                    "skills_missing": [],
                    "experience_match": True,
                    "created_at": "2026-09-05T00:00:00Z",
                }
            ]
        return table_mock

    mock_client.table.side_effect = table_side_effect
    return mock_client


@patch("app.routers.screenings.score_resume_against_posting")
@patch("app.routers.screenings.get_scoped_client")
@patch("app.routers.screenings.get_current_user_id", return_value="user-1")
def test_screens_single_resume_successfully(mock_user, mock_client_dep, mock_score):
    resumes = [{"id": "resume-1", "parsed_text": "...", "extracted_skills": ["python"], "experience_years": 5.0}]
    posting = {"id": "posting-1", "raw_text": "...", "required_skills": ["python"], "min_experience_years": 3.0}
    mock_client_dep.return_value = _mock_client_with_data(resumes, posting)
    mock_score.return_value = ScoreResult(
        overall_score=88.0, semantic_score=80.0, skill_score=100.0,
        skills_matched=["python"], skills_missing=[], experience_match=True,
    )

    response = client.post(
        "/screenings",
        json={"resume_ids": ["resume-1"], "job_posting_id": "posting-1"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["overall_score"] == 88.0
    assert body[0]["error"] is None


@patch("app.routers.screenings.get_scoped_client")
@patch("app.routers.screenings.get_current_user_id", return_value="user-1")
def test_rejects_batch_over_20_resumes(mock_user, mock_client_dep):
    response = client.post(
        "/screenings",
        json={"resume_ids": [f"resume-{i}" for i in range(21)], "job_posting_id": "posting-1"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 422


@patch("app.routers.screenings.score_resume_against_posting", side_effect=[Exception("boom")])
@patch("app.routers.screenings.get_scoped_client")
@patch("app.routers.screenings.get_current_user_id", return_value="user-1")
def test_partial_failure_does_not_fail_whole_batch(mock_user, mock_client_dep, mock_score):
    resumes = [{"id": "resume-1", "parsed_text": "...", "extracted_skills": [], "experience_years": None}]
    posting = {"id": "posting-1", "raw_text": "...", "required_skills": [], "min_experience_years": None}
    mock_client_dep.return_value = _mock_client_with_data(resumes, posting)

    response = client.post(
        "/screenings",
        json={"resume_ids": ["resume-1"], "job_posting_id": "posting-1"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body[0]["error"] == "boom"
    assert body[0]["overall_score"] is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_screenings_api.py -v`
Expected: FAIL (`app.routers.screenings` does not exist)

- [ ] **Step 4: Write `app/routers/screenings.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
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
        results.append(ScreeningResultResponse(resume_id=resume_id, **saved))

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
```

- [ ] **Step 5: Register the router in `app/main.py`**

```python
# Add to backend/app/main.py, after the job_postings import:
from app.routers import screenings

# Add after app.include_router(job_postings.router):
app.include_router(screenings.router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && pytest tests/test_screenings_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/screenings.py backend/app/main.py backend/tests/test_screenings_api.py
git commit -m "feat(backend): add screening endpoint with batch cap and per-item failure handling"
```

---

## Phase 5: Frontend Features

### Task 15: API client wrapper

**Files:**
- Create: `frontend/src/lib/api.ts`

**Interfaces:**
- Consumes: `supabase` (from `supabaseClient.ts`)
- Produces: `uploadResumeFile(file: File) -> Promise<{storage_path: string}>`, `createResume(storage_path: string, original_filename: string) -> Promise<Resume>`, `listResumes() -> Promise<Resume[]>`, `createJobPosting(data) -> Promise<JobPosting>`, `listJobPostings() -> Promise<JobPosting[]>`, `createScreenings(resume_ids: string[], job_posting_id: string) -> Promise<ScreeningResult[]>`, `listScreenings(params) -> Promise<ScreeningResult[]>`.

- [ ] **Step 1: Write `src/lib/api.ts`**

```typescript
import { supabase } from './supabaseClient';

const API_URL = import.meta.env.VITE_API_URL;

export interface Resume {
  id: string;
  storage_path: string;
  original_filename: string;
  parsed_text: string;
  extracted_skills: string[];
  experience_years: number | null;
  education_level: string | null;
  created_at: string;
}

export interface JobPosting {
  id: string;
  title: string;
  company: string | null;
  raw_text: string;
  required_skills: string[];
  min_experience_years: number | null;
  created_at: string;
}

export interface ScreeningResult {
  resume_id: string;
  error: string | null;
  id: string | null;
  overall_score: number | null;
  semantic_score: number | null;
  skill_score: number | null;
  skills_matched: string[] | null;
  skills_missing: string[] | null;
  experience_match: boolean | null;
  created_at: string | null;
}

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${token}` };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = { 'Content-Type': 'application/json', ...(await authHeaders()), ...options.headers };
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function uploadResumeFile(file: File): Promise<{ storage_path: string }> {
  const { data: sessionData } = await supabase.auth.getSession();
  const userId = sessionData.session?.user.id;
  if (!userId) throw new Error('Not authenticated');
  const storagePath = `${userId}/${Date.now()}-${file.name}`;
  const { error } = await supabase.storage.from('resumes').upload(storagePath, file);
  if (error) throw new Error(error.message);
  return { storage_path: storagePath };
}

export function createResume(storage_path: string, original_filename: string): Promise<Resume> {
  return request('/resumes', { method: 'POST', body: JSON.stringify({ storage_path, original_filename }) });
}

export function listResumes(): Promise<Resume[]> {
  return request('/resumes');
}

export function createJobPosting(data: {
  title: string;
  company?: string;
  raw_text: string;
  min_experience_years?: number;
}): Promise<JobPosting> {
  return request('/job-postings', { method: 'POST', body: JSON.stringify(data) });
}

export function listJobPostings(): Promise<JobPosting[]> {
  return request('/job-postings');
}

export function createScreenings(resume_ids: string[], job_posting_id: string): Promise<ScreeningResult[]> {
  return request('/screenings', { method: 'POST', body: JSON.stringify({ resume_ids, job_posting_id }) });
}

export function listScreenings(params: { job_posting_id?: string; resume_id?: string }): Promise<ScreeningResult[]> {
  const query = new URLSearchParams(params as Record<string, string>).toString();
  return request(`/screenings?${query}`);
}
```

- [ ] **Step 2: Manually verify**

In the browser console (with a logged-in session), run `await listResumes()` and confirm it returns `[]` (or existing resumes) without throwing.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add typed API client wrapper for backend endpoints"
```

---

### Task 16: Job seeker mode page

**Files:**
- Create: `frontend/src/components/ResumeUploader.tsx`
- Create: `frontend/src/components/ScoreBreakdown.tsx`
- Create: `frontend/src/pages/JobSeekerPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `uploadResumeFile`, `createResume`, `createJobPosting`, `createScreenings` (Task 15)
- Produces: the `/job-seeker` route rendering `JobSeekerPage`, replacing its placeholder.

- [ ] **Step 1: Write `src/components/ResumeUploader.tsx`**

```tsx
import { useState } from 'react';

interface Props {
  onFileSelected: (file: File) => void;
  busy: boolean;
}

export default function ResumeUploader({ onFileSelected, busy }: Props) {
  const [fileName, setFileName] = useState<string | null>(null);

  return (
    <div>
      <input
        type="file"
        accept=".pdf,.docx"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            setFileName(file.name);
            onFileSelected(file);
          }
        }}
      />
      {fileName && <p>Selected: {fileName}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Write `src/components/ScoreBreakdown.tsx`**

```tsx
import { ScreeningResult } from '../lib/api';

export default function ScoreBreakdown({ result }: { result: ScreeningResult }) {
  if (result.error) {
    return <p role="alert">Couldn't score this resume: {result.error}</p>;
  }
  return (
    <div>
      <h2>Overall match: {result.overall_score}%</h2>
      <p>Semantic fit: {result.semantic_score}% &middot; Skill overlap: {result.skill_score}%</p>
      <h3>Matched skills</h3>
      <p>{result.skills_matched?.join(', ') || 'None'}</p>
      <h3>Missing skills</h3>
      <p>{result.skills_missing?.join(', ') || 'None'}</p>
      {result.experience_match !== null && (
        <p>Experience requirement: {result.experience_match ? 'Met' : 'Not met'}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Write `src/pages/JobSeekerPage.tsx`**

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import ResumeUploader from '../components/ResumeUploader';
import ScoreBreakdown from '../components/ScoreBreakdown';
import { createJobPosting, createResume, createScreenings, uploadResumeFile, ScreeningResult } from '../lib/api';

export default function JobSeekerPage() {
  const [jobText, setJobText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScreeningResult | null>(null);

  async function handleFileSelected(file: File) {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const { storage_path } = await uploadResumeFile(file);
      const resume = await createResume(storage_path, file.name);
      if (!jobText.trim()) {
        setError('Paste a job description before checking your match');
        return;
      }
      const posting = await createJobPosting({ title: 'Job description', raw_text: jobText });
      const [screeningResult] = await createScreenings([resume.id], posting.id);
      setResult(screeningResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Check my resume against a job</h1>
      <nav><Link to="/job-seeker/history">View history</Link></nav>
      <textarea
        placeholder="Paste the job description here"
        value={jobText}
        onChange={(e) => setJobText(e.target.value)}
        rows={8}
      />
      <ResumeUploader onFileSelected={handleFileSelected} busy={busy} />
      {busy && <p>Scoring your resume&hellip; the first request after inactivity can take up to a minute while the server wakes up.</p>}
      {error && <p role="alert">{error}</p>}
      {result && <ScoreBreakdown result={result} />}
    </div>
  );
}
```

- [ ] **Step 4: Wire the route in `App.tsx`**

```tsx
// In frontend/src/App.tsx, replace the /job-seeker placeholder route:
import JobSeekerPage from './pages/JobSeekerPage';
// ...
<Route
  path="/job-seeker"
  element={<RequireAuth><JobSeekerPage /></RequireAuth>}
/>
```

- [ ] **Step 5: Manually verify**

Log in, paste a short job description, upload a real PDF or DOCX resume, and confirm the score breakdown renders with matched/missing skills. Try an unsupported file type and confirm the error message shows instead of a crash.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ResumeUploader.tsx frontend/src/components/ScoreBreakdown.tsx frontend/src/pages/JobSeekerPage.tsx frontend/src/App.tsx
git commit -m "feat(frontend): implement job seeker mode upload-and-check flow"
```

---

### Task 17: Job seeker history page

**Files:**
- Create: `frontend/src/pages/JobSeekerHistoryPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `listResumes`, `listScreenings` (Task 15)
- Produces: the `/job-seeker/history` route.

- [ ] **Step 1: Write `src/pages/JobSeekerHistoryPage.tsx`**

```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listResumes, listScreenings, Resume, ScreeningResult } from '../lib/api';

interface HistoryRow {
  resume: Resume | undefined;
  result: ScreeningResult;
}

export default function JobSeekerHistoryPage() {
  const [rows, setRows] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const resumes = await listResumes();
      const allResults: HistoryRow[] = [];
      for (const resume of resumes) {
        const results = await listScreenings({ resume_id: resume.id });
        for (const result of results) {
          allResults.push({ resume, result });
        }
      }
      setRows(allResults);
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <p>Loading history&hellip;</p>;

  return (
    <div>
      <h1>Your past checks</h1>
      <nav><Link to="/job-seeker">Back to checker</Link></nav>
      {rows.length === 0 && <p>No checks yet.</p>}
      <ul>
        {rows.map(({ resume, result }) => (
          <li key={result.id}>
            {resume?.original_filename} &mdash; {result.overall_score}% match
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Wire the route in `App.tsx`**

```tsx
// In frontend/src/App.tsx:
import JobSeekerHistoryPage from './pages/JobSeekerHistoryPage';
// ...
<Route
  path="/job-seeker/history"
  element={<RequireAuth><JobSeekerHistoryPage /></RequireAuth>}
/>
```

- [ ] **Step 3: Manually verify**

After running a couple of checks on the job seeker page, visit `/job-seeker/history` and confirm each past check is listed with its filename and score.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/JobSeekerHistoryPage.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add job seeker history page"
```

---

### Task 18: Recruiter mode page

**Files:**
- Create: `frontend/src/components/CandidateRankingTable.tsx`
- Create: `frontend/src/pages/RecruiterPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `createJobPosting`, `uploadResumeFile`, `createResume`, `createScreenings` (Task 15)
- Produces: the `/recruiter` route, replacing its placeholder.

- [ ] **Step 1: Write `src/components/CandidateRankingTable.tsx`**

```tsx
import { ScreeningResult } from '../lib/api';

interface Props {
  results: ScreeningResult[];
  filenamesByResumeId: Record<string, string>;
}

export default function CandidateRankingTable({ results, filenamesByResumeId }: Props) {
  const sorted = [...results].sort((a, b) => (b.overall_score ?? -1) - (a.overall_score ?? -1));

  return (
    <table>
      <thead>
        <tr>
          <th>Candidate</th>
          <th>Score</th>
          <th>Matched skills</th>
          <th>Missing skills</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((result) => (
          <tr key={result.resume_id}>
            <td>{filenamesByResumeId[result.resume_id] ?? result.resume_id}</td>
            <td>{result.error ? `Error: ${result.error}` : `${result.overall_score}%`}</td>
            <td>{result.skills_matched?.join(', ') ?? ''}</td>
            <td>{result.skills_missing?.join(', ') ?? ''}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 2: Write `src/pages/RecruiterPage.tsx`**

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import CandidateRankingTable from '../components/CandidateRankingTable';
import { createJobPosting, createResume, createScreenings, uploadResumeFile, ScreeningResult } from '../lib/api';

const MAX_BATCH = 20;

export default function RecruiterPage() {
  const [title, setTitle] = useState('');
  const [jobText, setJobText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ScreeningResult[]>([]);
  const [filenamesByResumeId, setFilenamesByResumeId] = useState<Record<string, string>>({});

  async function handleFilesSelected(files: FileList) {
    if (!title.trim() || !jobText.trim()) {
      setError('Enter a job title and description first');
      return;
    }
    if (files.length > MAX_BATCH) {
      setError(`You can screen at most ${MAX_BATCH} resumes at once`);
      return;
    }
    setBusy(true);
    setError(null);
    setResults([]);
    try {
      const posting = await createJobPosting({ title, raw_text: jobText });
      const resumeIds: string[] = [];
      const names: Record<string, string> = {};
      for (const file of Array.from(files)) {
        const { storage_path } = await uploadResumeFile(file);
        const resume = await createResume(storage_path, file.name);
        resumeIds.push(resume.id);
        names[resume.id] = file.name;
      }
      setFilenamesByResumeId(names);
      const screeningResults = await createScreenings(resumeIds, posting.id);
      setResults(screeningResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Screen candidates for a job posting</h1>
      <nav><Link to="/recruiter/history">View history</Link></nav>
      <input placeholder="Job title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <textarea
        placeholder="Paste the job description here"
        value={jobText}
        onChange={(e) => setJobText(e.target.value)}
        rows={8}
      />
      <input
        type="file"
        accept=".pdf,.docx"
        multiple
        disabled={busy}
        onChange={(e) => e.target.files && handleFilesSelected(e.target.files)}
      />
      {busy && <p>Screening candidates&hellip; the first request after inactivity can take up to a minute while the server wakes up.</p>}
      {error && <p role="alert">{error}</p>}
      {results.length > 0 && (
        <CandidateRankingTable results={results} filenamesByResumeId={filenamesByResumeId} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Wire the route in `App.tsx`**

```tsx
// In frontend/src/App.tsx, replace the /recruiter placeholder route:
import RecruiterPage from './pages/RecruiterPage';
// ...
<Route
  path="/recruiter"
  element={<RequireAuth><RecruiterPage /></RequireAuth>}
/>
```

- [ ] **Step 4: Manually verify**

Log in, enter a job title and description, upload 2-3 resumes at once, and confirm a ranked table appears sorted by score with matched/missing skills per row. Try uploading more than 20 files and confirm the batch-size error shows instead of submitting.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CandidateRankingTable.tsx frontend/src/pages/RecruiterPage.tsx frontend/src/App.tsx
git commit -m "feat(frontend): implement recruiter mode batch screening and ranking"
```

---

### Task 19: Recruiter history page

**Files:**
- Create: `frontend/src/pages/RecruiterHistoryPage.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `listJobPostings`, `listScreenings` (Task 15)
- Produces: the `/recruiter/history` route.

- [ ] **Step 1: Write `src/pages/RecruiterHistoryPage.tsx`**

```tsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { JobPosting, listJobPostings, listScreenings, ScreeningResult } from '../lib/api';

interface PostingWithResults {
  posting: JobPosting;
  results: ScreeningResult[];
}

export default function RecruiterHistoryPage() {
  const [entries, setEntries] = useState<PostingWithResults[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const postings = await listJobPostings();
      const entries: PostingWithResults[] = [];
      for (const posting of postings) {
        const results = await listScreenings({ job_posting_id: posting.id });
        entries.push({ posting, results });
      }
      setEntries(entries);
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <p>Loading history&hellip;</p>;

  return (
    <div>
      <h1>Past job postings</h1>
      <nav><Link to="/recruiter">Back to screener</Link></nav>
      {entries.length === 0 && <p>No postings yet.</p>}
      {entries.map(({ posting, results }) => (
        <section key={posting.id}>
          <h2>{posting.title}</h2>
          <p>{results.length} candidate(s) screened</p>
          <ul>
            {results
              .slice()
              .sort((a, b) => (b.overall_score ?? -1) - (a.overall_score ?? -1))
              .map((result) => (
                <li key={result.resume_id}>{result.overall_score}% match</li>
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Wire the route in `App.tsx`**

```tsx
// In frontend/src/App.tsx:
import RecruiterHistoryPage from './pages/RecruiterHistoryPage';
// ...
<Route
  path="/recruiter/history"
  element={<RequireAuth><RecruiterHistoryPage /></RequireAuth>}
/>
```

- [ ] **Step 3: Manually verify**

After screening a batch of candidates on the recruiter page, visit `/recruiter/history` and confirm the posting appears with its candidate count and sorted scores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RecruiterHistoryPage.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add recruiter history page"
```

---

## Phase 6: Deployment

### Task 20: Deploy backend to Render

**Files:**
- Create: `backend/render.yaml`

**Interfaces:**
- Produces: a deployed backend at `https://<service-name>.onrender.com`.

- [ ] **Step 1: Write `render.yaml`**

```yaml
services:
  - type: web
    name: resume-screener-api
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_ANON_KEY
        sync: false
      - key: SUPABASE_JWT_SECRET
        sync: false
      - key: CORS_ORIGINS
        sync: false
```

- [ ] **Step 2: Push to GitHub, connect Render**

Push the repo to GitHub. In the Render dashboard: New → Web Service → select the repo → set Root Directory to `backend`. Render will detect `render.yaml`; confirm the build/start commands match Step 1.

- [ ] **Step 3: Set environment variables in the Render dashboard**

Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` (from the Supabase project's API settings) and `CORS_ORIGINS` (as a JSON array string, e.g. `["https://your-app.vercel.app"]` — update this once the frontend URL from Task 21 is known).

- [ ] **Step 4: Deploy and verify**

Run: `curl https://<service-name>.onrender.com/health`
Expected: `{"status":"ok"}` (allow up to a minute for the first request if the service just spun up)

- [ ] **Step 5: Commit**

```bash
git add backend/render.yaml
git commit -m "chore(backend): add Render deployment config"
```

---

### Task 21: Deploy frontend to Vercel

**Files:**
- Create: `frontend/vercel.json`

**Interfaces:**
- Produces: a deployed frontend at `https://<project-name>.vercel.app`, which becomes the public demo link.

- [ ] **Step 1: Write `vercel.json`** (ensures client-side routing works on refresh)

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

- [ ] **Step 2: Import the project in Vercel**

In the Vercel dashboard: Add New → Project → select the repo → set Root Directory to `frontend` → framework preset "Vite" (should auto-detect).

- [ ] **Step 3: Set environment variables in the Vercel dashboard**

`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (from the Supabase project), `VITE_API_URL` set to the Render URL from Task 20.

- [ ] **Step 4: Deploy and update backend CORS**

Deploy. Take the resulting Vercel URL and update the Render backend's `CORS_ORIGINS` env var to include it, then redeploy the backend so it accepts requests from the live frontend.

- [ ] **Step 5: Commit**

```bash
git add frontend/vercel.json
git commit -m "chore(frontend): add Vercel routing config"
```

---

### Task 22: End-to-end smoke test on the deployed app

**Files:** None (manual verification against the live deployment)

- [ ] **Step 1: Job seeker flow**

Visit the Vercel URL, sign up, paste a job description, upload a real resume, and confirm a score with matched/missing skills renders. Expect a cold-start delay on the first request.

- [ ] **Step 2: Recruiter flow**

Create a job posting, upload 2-3 resumes at once, and confirm a ranked table renders sorted by score.

- [ ] **Step 3: History**

Revisit `/job-seeker/history` and `/recruiter/history` and confirm prior results from Steps 1-2 appear.

- [ ] **Step 4: Cross-account isolation**

Sign up a second account and confirm it sees no resumes/postings/results from the first account (verifies the RLS policies from Task 2 are actually enforced end-to-end, not just present in the schema).

- [ ] **Step 5: Record the live URL**

Note the Vercel URL somewhere durable (resume, portfolio site) now that the smoke test has passed.
