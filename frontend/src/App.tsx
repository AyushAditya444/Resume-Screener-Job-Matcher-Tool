import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import type { Role } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import JobSeekerPage from './pages/JobSeekerPage';
import JobSeekerHistoryPage from './pages/JobSeekerHistoryPage';
import RecruiterPage from './pages/RecruiterPage';
import RecruiterHistoryPage from './pages/RecruiterHistoryPage';

function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { session, role: userRole, loading } = useAuth();
  if (loading) return <p>Loading...</p>;
  if (!session) return <Navigate to="/login" replace />;
  if (userRole !== role) {
    return <Navigate to={userRole === 'recruiter' ? '/recruiter' : '/job-seeker'} replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/job-seeker"
            element={<RequireRole role="job_seeker"><JobSeekerPage /></RequireRole>}
          />
          <Route
            path="/job-seeker/history"
            element={<RequireRole role="job_seeker"><JobSeekerHistoryPage /></RequireRole>}
          />
          <Route
            path="/recruiter"
            element={<RequireRole role="recruiter"><RecruiterPage /></RequireRole>}
          />
          <Route
            path="/recruiter/history"
            element={<RequireRole role="recruiter"><RecruiterHistoryPage /></RequireRole>}
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
