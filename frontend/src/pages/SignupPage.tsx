import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../context/AuthContext';

export default function SignupPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>('job_seeker');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const { error } = await signUp(email, password, role);
    if (error) {
      setError(error);
      return;
    }
    navigate(role === 'recruiter' ? '/recruiter' : '/job-seeker');
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Sign up</h1>
      {error && <p role="alert">{error}</p>}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <fieldset>
        <legend>I am a...</legend>
        <label>
          <input
            type="radio"
            name="role"
            value="job_seeker"
            checked={role === 'job_seeker'}
            onChange={() => setRole('job_seeker')}
          />
          Job Seeker
        </label>
        <label>
          <input
            type="radio"
            name="role"
            value="recruiter"
            checked={role === 'recruiter'}
            onChange={() => setRole('recruiter')}
          />
          Recruiter
        </label>
      </fieldset>
      <button type="submit">Sign up</button>
      <p>Already have an account? <Link to="/login">Log in</Link></p>
    </form>
  );
}
