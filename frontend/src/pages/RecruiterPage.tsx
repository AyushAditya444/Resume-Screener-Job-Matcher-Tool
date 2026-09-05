import { useState } from 'react';
import { Link } from 'react-router-dom';
import CandidateRankingTable from '../components/CandidateRankingTable';
import { createJobPosting, createResume, createScreenings, uploadResumeFile } from '../lib/api';
import type { ScreeningResult } from '../lib/api';

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
