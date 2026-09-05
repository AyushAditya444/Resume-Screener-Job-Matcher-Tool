import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listJobPostings, listScreenings } from '../lib/api';
import type { JobPosting, ScreeningResult } from '../lib/api';

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
