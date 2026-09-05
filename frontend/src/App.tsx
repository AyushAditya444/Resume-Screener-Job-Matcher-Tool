import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

function Placeholder({ label }: { label: string }) {
  return <div>{label}</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Placeholder label="Login" />} />
        <Route path="/job-seeker" element={<Placeholder label="Job Seeker" />} />
        <Route path="/recruiter" element={<Placeholder label="Recruiter" />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
