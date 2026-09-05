-- supabase/migrations/0002_auto_create_profile.sql
--
-- 0001_init.sql created the profiles table (referenced by resumes,
-- job_postings, and screening_results via foreign key) but nothing ever
-- populated it: signing up only creates a row in Supabase's own
-- auth.users table, so every insert into resumes/job_postings/
-- screening_results was failing with a foreign key violation
-- ("Key is not present in table 'profiles'").
--
-- This trigger auto-creates the matching profiles row whenever a new
-- user signs up, and backfills any accounts created before this fix.

create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id)
  values (new.id)
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Backfill profiles for accounts that signed up before this trigger existed.
insert into public.profiles (id)
select id from auth.users
on conflict (id) do nothing;
