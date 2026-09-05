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
