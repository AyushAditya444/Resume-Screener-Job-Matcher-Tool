import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listResumes, listScreenings } from '../lib/api';
import type { Resume, ScreeningResult } from '../lib/api';

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
