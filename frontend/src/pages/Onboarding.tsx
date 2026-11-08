import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../authContext';
import type { AuthUser } from '../authContext';

const SCHOOLS = [
  'Maplewood High School',
  'Riverside Academy',
  'Oakhill College',
  'Cedar Valley School',
  'Summit Preparatory',
  'Greenfield Institute',
  'Other',
];

export default function Onboarding() {
  const { user, setUser, loading } = useAuth();
  const navigate = useNavigate();
  const [school, setSchool] = useState('');
  const [customSchool, setCustomSchool] = useState('');
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [preferredGrade, setPreferredGrade] = useState<number | null>(user?.preferred_grade ?? null);
  const [subjects, setSubjects] = useState<{ id: string; name: string }[]>([]);
  const [preferredSubjects, setPreferredSubjects] = useState<string[]>(user?.preferred_subject_ids ?? []);
  const [subjectsError, setSubjectsError] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  const resolvedSchool = school === 'Other' ? customSchool : school;

  useEffect(() => {
    const controller = new AbortController();
    api<{ id: string; name: string }[]>('/api/v1/taxonomy/subjects', { signal: controller.signal })
      .then((result) => {
        if (!Array.isArray(result)) throw new Error('The subject catalog was not in the expected format.');
        if (!controller.signal.aborted) {
          setSubjects(result);
          setSubjectsError('');
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setSubjectsError(reason instanceof Error ? reason.message : 'The subject catalog could not be loaded.');
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      navigate('/login', { replace: true });
      return;
    }
    if (user.role === 'admin' || user.onboarding_completed) {
      navigate('/', { replace: true });
    }
  }, [user, loading, navigate]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setFeedback('');
    if (!termsAccepted) {
      setError('You must accept the terms to continue.');
      return;
    }
    if (!resolvedSchool?.trim()) {
      setError('Please select or enter your school.');
      return;
    }
    setSubmitting(true);
    try {
      const result = await api<AuthUser>('/api/v1/auth/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          school: resolvedSchool.trim(),
          display_name: displayName.trim() || null,
          preferred_grade: preferredGrade,
          preferred_subject_ids: preferredSubjects,
          terms_accepted: true,
        }),
      });
      setUser(result);
      setFeedback('Your account is ready. Welcome to Recall Atlas.');
      setTimeout(() => navigate('/', { replace: true }), 800);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : 'Onboarding could not be completed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page-content auth-page">
      <div className="page-heading">
        <p className="eyebrow">Recall Atlas account</p>
        <h1>Complete your profile</h1>
        <p className="page-description">Help us personalize Recall Atlas. Your school affiliation is self-reported and not independently verified.</p>
      </div>
      <form className="auth-form card-surface" onSubmit={submit}>
        <label>
          <span className="form-label">School</span>
          <select
            value={school}
            onChange={(event) => setSchool(event.target.value)}
            required
          >
            <option value="">Select your school</option>
            {SCHOOLS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          {school === 'Other' && (
            <label style={{ display: 'block', marginTop: 8 }}>
              <span className="form-label">Enter your school</span>
              <input
                autoComplete="off"
                onChange={(event) => setCustomSchool(event.target.value)}
                required
                type="text"
                value={customSchool}
              />
            </label>
          )}
        </label>
        <label>
          <span className="form-label">Display name</span>
          <input
            autoComplete="name"
            onChange={(event) => setDisplayName(event.target.value)}
            type="text"
            value={displayName}
          />
          <span className="form-hint">Shown on your account and any contributions you make.</span>
        </label>
        <fieldset className="grade-preference">
          <legend className="form-label">What grade are you studying?</legend>
          <p className="form-hint">We’ll use this to surface relevant past papers. You can skip this.</p>
          <div className="grade-options">
            {[9, 10, 11, 12].map((grade) => (
              <button
                aria-pressed={preferredGrade === grade}
                className={`grade-option ${preferredGrade === grade ? 'is-selected' : ''}`}
                key={grade}
                onClick={() => setPreferredGrade(preferredGrade === grade ? null : grade)}
                type="button"
              >
                Grade {grade}
              </button>
            ))}
          </div>
        </fieldset>
        {subjects.length > 0 && (
          <fieldset className="grade-preference">
            <legend className="form-label">What subjects interest you?</legend>
            <p className="form-hint">Choose any that you’d like us to prioritize.</p>
            <div className="subject-options">
              {subjects.map((subject) => (
                <label className="subject-option" key={subject.id}>
                  <input
                    checked={preferredSubjects.includes(subject.id)}
                    onChange={(event) => setPreferredSubjects((current) => event.target.checked
                      ? [...current, subject.id]
                      : current.filter((id) => id !== subject.id))}
                    type="checkbox"
                  />
                  <span>{subject.name}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}
        {subjectsError && <p className="inline-error" role="alert">{subjectsError}</p>}
        <label style={{ display: 'flex', alignItems: 'start', gap: 10, paddingTop: 6 }}>
          <input
            checked={termsAccepted}
            onChange={(event) => setTermsAccepted(event.target.checked)}
            type="checkbox"
          />
          <span>
            I accept the <Link to="/terms">Terms of Service</Link> and understand that school affiliation is self-reported.
          </span>
        </label>
        {error && <p className="inline-error" role="alert">{error}</p>}
        {feedback && <p className="inline-feedback" role="status">{feedback}</p>}
        <button className="button button-primary" disabled={submitting} type="submit">
          {submitting ? 'Please wait…' : 'Continue to Recall Atlas'}
        </button>
      </form>
      <p className="auth-switch">
        Already have an account?{' '}
        <Link to="/login">Sign in</Link>
      </p>
    </section>
  );
}
