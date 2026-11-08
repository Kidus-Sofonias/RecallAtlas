import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../authContext';
import type { AuthUser } from '../authContext';

type Mode = 'login' | 'register' | 'reset-request' | 'reset-complete' | 'verify';

export default function Auth({ mode }: { mode: Mode }) {
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setUser, user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const token = searchParams.get('token') || new URLSearchParams(window.location.hash.slice(1)).get('token') || '';

  useEffect(() => {
    if (authLoading || !user) return;
    navigate(user.role === 'admin' || user.onboarding_completed ? '/' : '/onboarding', { replace: true });
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (mode !== 'verify') return;
    let active = true;
    if (!token) return;
    api('/api/v1/auth/verify-email', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
      .then(() => { if (active) setFeedback('Your email is verified. You can now sign in.'); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Email verification failed.');
      });
    return () => { active = false; };
  }, [mode, token]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setFeedback('');
    try {
      if (mode === 'login') {
        const result = await api<{ user: AuthUser }>('/api/v1/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        });
        setUser(result.user);
        const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
        navigate(from || '/', { replace: true });
      } else if (mode === 'register') {
        const result = await api<{ user?: AuthUser }>('/api/v1/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        });
        if (result.user) {
          setUser(result.user);
          navigate(result.user.role === 'admin' || result.user.onboarding_completed ? '/' : '/onboarding', { replace: true });
        } else {
          setFeedback('If the address can be registered, a verification email will be sent.');
        }
      } else if (mode === 'reset-request') {
        await api('/api/v1/auth/password-reset/request', {
          method: 'POST',
          body: JSON.stringify({ email }),
        });
        setFeedback('If an active account uses that address, password reset instructions will be sent.');
      } else if (mode === 'reset-complete') {
        await api('/api/v1/auth/password-reset/complete', {
          method: 'POST',
          body: JSON.stringify({ token, password }),
        });
        setFeedback('Your password was updated. Sign in with the new password.');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request could not be completed.');
    } finally {
      setLoading(false);
    }
  }

  const title = {
    login: 'Sign in',
    register: 'Create an account',
    'reset-request': 'Reset your password',
    'reset-complete': 'Choose a new password',
    verify: 'Verify your email',
  }[mode];
  const displayedError = mode === 'verify' && !token
    ? 'This verification link is missing its token.'
    : error;

  return (
    <section className="page-content auth-page">
      <div className="page-heading">
        <p className="eyebrow">Recall Atlas account</p>
        <h1>{title}</h1>
        <p className="page-description">Sign in to access your study collections, bookmarks, and personalized workspace.</p>
      </div>
      <form className="auth-form card-surface" onSubmit={(event) => void submit(event)}>
        {(mode === 'login' || mode === 'register' || mode === 'reset-request') && (
          <label>
            <span className="form-label">Email address</span>
            <input autoComplete="email" onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required type="email" value={email} />
          </label>
        )}
        {(mode === 'login' || mode === 'register' || mode === 'reset-complete') && (
          <label>
            <span className="form-label">{mode === 'reset-complete' ? 'New password' : 'Password'}</span>
            <input
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={mode === 'login' ? 'Enter your password' : 'Create a password'}
              required
              type="password"
              value={password}
            />
            {(mode === 'register' || mode === 'reset-complete') && (
              <span className="form-hint">Use 8–128 characters.</span>
            )}
          </label>
        )}
        {displayedError && <p className="inline-error" role="alert">{displayedError}</p>}
        {feedback && <p className="inline-feedback" role="status">{feedback}</p>}
        {mode !== 'verify' && (
          <button className="button button-primary" disabled={loading} type="submit">
            {loading ? 'Please wait…' : title}
          </button>
        )}
        {mode === 'login' && <p className="auth-switch"><Link to="/reset-password">Forgot your password?</Link></p>}
      </form>
      <p className="auth-switch">
        {mode === 'login'
          ? <>New to Recall Atlas? <Link to="/register">Create an account</Link></>
          : mode === 'register'
            ? <>Already have an account? <Link to="/login">Sign in</Link></>
            : <>Back to <Link to="/login">Sign in</Link></>}
      </p>
    </section>
  );
}

export function PasswordReset() {
  const [searchParams] = useSearchParams();
  const hashParams = new URLSearchParams(window.location.hash.slice(1));
  return <Auth mode={searchParams.has('token') || hashParams.has('token') ? 'reset-complete' : 'reset-request'} />;
}
