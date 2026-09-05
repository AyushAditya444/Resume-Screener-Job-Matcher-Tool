import type { ScreeningResult } from '../lib/api';

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
