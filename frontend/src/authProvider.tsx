import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ApiError, api } from './api';
import { AuthContext } from './authContext';
import type { AuthUser } from './authContext';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api<AuthUser>('/api/v1/auth/me')
      .then((result) => { if (active) setUser(result); })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          setUser(null);
          return;
        }
        setError(reason instanceof Error ? reason.message : 'Your account status could not be checked.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return <AuthContext.Provider value={{ user, loading, error, setUser }}>{children}</AuthContext.Provider>;
}
