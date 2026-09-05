import { useState } from 'react';
import { Link } from 'react-router-dom';
import ResumeUploader from '../components/ResumeUploader';
import ScoreBreakdown from '../components/ScoreBreakdown';
import { createJobPosting, createResume, createScreenings, uploadResumeFile } from '../lib/api';
import type { ScreeningResult } from '../lib/api';

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
