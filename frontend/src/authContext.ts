import { createContext, useContext } from 'react';

export type AuthUser = {
  id: string;
  email: string | null;
  display_name: string | null;
  school?: string | null;
  role: string;
  onboarding_completed: boolean;
  preferred_grade: number | null;
  preferred_subject_ids: string[];
};

export type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  error: string;
  setUser: (user: AuthUser | null) => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider.');
  return context;
}
