import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import JobSeekerPage from './pages/JobSeekerPage';
import JobSeekerHistoryPage from './pages/JobSeekerHistoryPage';
import RecruiterPage from './pages/RecruiterPage';

function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  if (loading) return <p>Loading...</p>;
  if (!session) return <Navigate to="/login" replace />;
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
            element={<RequireAuth><JobSeekerPage /></RequireAuth>}
          />
          <Route
            path="/job-seeker/history"
            element={<RequireAuth><JobSeekerHistoryPage /></RequireAuth>}
          />
          <Route
            path="/recruiter"
            element={<RequireAuth><RecruiterPage /></RequireAuth>}
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
