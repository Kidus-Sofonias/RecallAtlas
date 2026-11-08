import { useEffect, useState } from 'react';
import { api } from '../api';

type Notification = { id: string; title: string; body: string; read: boolean; created_at: string | null };

export default function Notifications() {
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [savingId, setSavingId] = useState('');

  useEffect(() => {
    let active = true;
    api<Notification[]>('/api/v1/notifications')
      .then((result) => {
        if (!Array.isArray(result)) throw new Error('The notifications response was not in the expected format.');
        if (active) setItems(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Notifications could not be loaded.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const unreadCount = items.filter((item) => !item.read).length;

  async function markRead(id: string) {
    setSavingId(id);
    setError('');
    try {
      await api(`/api/v1/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' });
      setItems((current) => current.map((item) => item.id === id ? { ...item, read: true } : item));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The notification could not be marked as read.');
    } finally {
      setSavingId('');
    }
  }

  return (
    <section className="page-content">
      <div className="page-heading notification-heading">
        <div>
          <p className="eyebrow">Your account activity</p>
          <h1>Notifications</h1>
          <p className="page-description">Updates from your academic archive.</p>
        </div>
        {!loading && items.length > 0 && (
          <span className="unread-count">{unreadCount} unread</span>
        )}
      </div>

      {error && <div className="inline-error" role="alert">{error}</div>}
      {loading ? (
        <div aria-label="Loading notifications" className="loading-list" role="status"><span /><span /><span /></div>
      ) : items.length === 0 && !error ? (
        <div className="state-card">
          <span className="state-symbol">○</span>
          <strong>You are all caught up</strong>
          <p>New updates will appear here when they are available.</p>
        </div>
      ) : (
        <div aria-label="Notification history" className="notification-list">
          {items.map((item) => (
            <article className={`notification-item ${item.read ? '' : 'notification-unread'}`} key={item.id}>
              <span aria-hidden="true" className="notification-icon">{item.read ? '·' : '✳'}</span>
              <div>
                <div className="notification-title-row">
                  <h2>{item.title}</h2>
                  {!item.read && <span className="unread-dot" aria-label="Unread" />}
                </div>
                <p>{item.body}</p>
                <span className="notification-time">{item.created_at || 'Notification'}</span>
              </div>
              {!item.read && (
                <button
                  className="text-link"
                  disabled={savingId === item.id}
                  onClick={() => void markRead(item.id)}
                  type="button"
                >
                  {savingId === item.id ? 'Saving…' : 'Mark read'}
                </button>
              )}
            </article>
          ))}
        </div>
      )}
      {!loading && items.length > 0 && (
        <p className="quiet-note">Security and account-protection notices remain available in your notification history.</p>
      )}
    </section>
  );
}
