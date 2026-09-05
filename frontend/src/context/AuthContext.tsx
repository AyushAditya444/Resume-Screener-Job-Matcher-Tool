import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabaseClient';

export type Role = 'job_seeker' | 'recruiter';

interface AuthContextValue {
  session: Session | null;
  role: Role | null;
  loading: boolean;
  signUp: (email: string, password: string, role: Role) => Promise<{ error: string | null; role: Role | null }>;
  signIn: (email: string, password: string) => Promise<{ error: string | null; role: Role | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function fetchRole(userId: string): Promise<Role | null> {
  const { data } = await supabase.from('profiles').select('role').eq('id', userId).single();
  return (data?.role as Role | undefined) ?? null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function init() {
      const { data } = await supabase.auth.getSession();
      setSession(data.session);
      if (data.session) {
        setRole(await fetchRole(data.session.user.id));
      }
      setLoading(false);
    }
    init();

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      if (newSession) {
        fetchRole(newSession.user.id).then(setRole);
      } else {
        setRole(null);
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  async function signUp(email: string, password: string, chosenRole: Role) {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) return { error: error.message, role: null };
    if (data.session) {
      await supabase.from('profiles').update({ role: chosenRole }).eq('id', data.session.user.id);
      setRole(chosenRole);
    }
    return { error: null, role: chosenRole };
  }

  async function signIn(email: string, password: string) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error: error.message, role: null };
    const fetchedRole = data.session ? await fetchRole(data.session.user.id) : null;
    setRole(fetchedRole);
    return { error: null, role: fetchedRole };
  }

  async function signOut() {
    await supabase.auth.signOut();
  }

  return (
    <AuthContext.Provider value={{ session, role, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
