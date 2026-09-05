import type { ScreeningResult } from '../lib/api';

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
