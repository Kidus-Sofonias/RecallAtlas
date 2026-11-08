import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../authContext';
import type { AuthUser } from '../authContext';

export default function Account() {
  const { user, setUser } = useAuth();
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [preferredGrade, setPreferredGrade] = useState(user?.preferred_grade ? String(user.preferred_grade) : '');
  const [displayName, setDisplayName] = useState(user?.display_name ?? '');
  const [school, setSchool] = useState('');
  const [subjects, setSubjects] = useState<{ id: string; name: string }[]>([]);
  const [preferredSubjects, setPreferredSubjects] = useState<string[]>(user?.preferred_subject_ids ?? []);
  const [subjectsError, setSubjectsError] = useState('');
  const [savingPreference, setSavingPreference] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [requestingDeletion, setRequestingDeletion] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    api<{ display_name: string | null; school: string | null }>('/api/v1/me')
      .then((profile) => {
        if (active) {
          setDisplayName(profile.display_name ?? '');
          setSchool(profile.school ?? '');
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Your profile could not be loaded.');
      });
    api<{ id: string; name: string }[]>('/api/v1/taxonomy/subjects')
      .then((items) => {
        if (!Array.isArray(items)) throw new Error('The subject catalog was not in the expected format.');
        if (active) setSubjects(items);
      })
      .catch((reason: unknown) => {
        if (active) setSubjectsError(reason instanceof Error ? reason.message : 'The subject catalog could not be loaded.');
      });
    return () => { active = false; };
  }, []);

  async function saveProfile() {
    setSavingProfile(true);
    setError('');
    setFeedback('');
    try {
      const updated = await api<AuthUser>('/api/v1/me', {
        method: 'PATCH',
        body: JSON.stringify({ display_name: displayName, school }),
      });
      if (user) setUser({ ...user, display_name: updated.display_name, school: updated.school });
      setFeedback('Your profile has been updated.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your profile could not be saved.');
    } finally {
      setSavingProfile(false);
    }
  }

  async function signOut() {
    setLoading(true);
    setError('');
    try {
      await api('/api/v1/auth/logout', { method: 'POST' });
      setUser(null);
      navigate('/login', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign out could not be completed.');
    } finally {
      setLoading(false);
    }
  }

  async function savePreference() {
    setSavingPreference(true);
    setError('');
    setFeedback('');
    try {
      const updated = await api<AuthUser>('/api/v1/auth/preferences', {
        method: 'PATCH',
        body: JSON.stringify({
          preferred_grade: preferredGrade ? Number(preferredGrade) : null,
          preferred_subject_ids: preferredSubjects,
        }),
      });
      setUser(updated);
      setPreferredSubjects(updated.preferred_subject_ids);
      setFeedback('Your recommendations have been updated.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your preference could not be saved.');
    } finally {
      setSavingPreference(false);
    }
  }

  async function requestDeletion() {
    if (!window.confirm('Submit an account deletion request? This will sign you out.')) return;
    setRequestingDeletion(true);
    setError('');
    try {
      await api('/api/v1/me/deletion-request', {
        method: 'POST',
        body: JSON.stringify({ confirm: true }),
      });
      setUser(null);
      navigate('/login', { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Your deletion request could not be submitted.');
    } finally {
      setRequestingDeletion(false);
    }
  }

  return (
    <section className="page-content">
      <div className="page-heading">
        <p className="eyebrow">Your account</p>
        <h1>Account</h1>
        <p className="page-description">Your private Recall Atlas profile.</p>
      </div>
      <div className="auth-form card-surface">
        <p>{user?.email}</p>
        <label>
          <span className="form-label">Display name</span>
          <input maxLength={100} onChange={(event) => setDisplayName(event.target.value)} value={displayName} />
        </label>
        <label>
          <span className="form-label">School (self-reported)</span>
          <input maxLength={200} onChange={(event) => setSchool(event.target.value)} value={school} />
        </label>
        <button className="button button-secondary" disabled={savingProfile} onClick={() => void saveProfile()} type="button">
          {savingProfile ? 'Saving…' : 'Save profile'}
        </button>
        <label>
          <span className="form-label">Study recommendations</span>
          <select onChange={(event) => setPreferredGrade(event.target.value)} value={preferredGrade}>
            <option value="">All grades</option>
            {[9, 10, 11, 12].map((grade) => <option key={grade} value={grade}>Grade {grade}</option>)}
          </select>
          <span className="form-hint">Choose a grade to personalize your home feed.</span>
        </label>
        {subjects.length > 0 && (
          <fieldset className="grade-preference">
            <legend className="form-label">Subjects you’re interested in</legend>
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
        {feedback && <p className="inline-feedback" role="status">{feedback}</p>}
        {error && <p className="inline-error" role="alert">{error}</p>}
        <button className="button button-secondary" disabled={savingPreference} onClick={() => void savePreference()} type="button">
          {savingPreference ? 'Saving…' : 'Save preference'}
        </button>
        <button className="button button-secondary" disabled={loading} onClick={() => void signOut()} type="button">
          {loading ? 'Signing out…' : 'Sign out'}
        </button>
        <button className="button button-secondary" disabled={requestingDeletion} onClick={() => void requestDeletion()} type="button">
          {requestingDeletion ? 'Submitting request…' : 'Request account deletion'}
        </button>
        <p className="form-hint">Submitting a request revokes your active sessions. Personal-data deletion and contribution anonymization require administrator processing.</p>
      </div>
    </section>
  );
}
