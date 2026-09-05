-- supabase/migrations/0003_add_role_to_profiles.sql
--
-- Adds a role to each account so job-seeker and recruiter mode can be
-- locked per-user instead of being freely switchable via the URL.
-- Existing accounts (created before this feature existed) default to
-- 'job_seeker' automatically via the column default.

alter table profiles
  add column role text not null default 'job_seeker'
  check (role in ('job_seeker', 'recruiter'));
