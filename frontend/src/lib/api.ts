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
