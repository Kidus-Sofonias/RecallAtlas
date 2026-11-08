import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

type Bookmark = { id: string; target_type: string; target_id: string };

function destination(item: Bookmark): string | null {
  if (item.target_type === 'question') return `/questions/${item.target_id}`;
  if (item.target_type === 'document') return `/documents/${item.target_id}`;
  return null;
}

export default function Bookmarks() {
  const [items, setItems] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [removing, setRemoving] = useState('');
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    let active = true;
    api<Bookmark[]>('/api/v1/bookmarks')
      .then((result) => {
        if (!Array.isArray(result)) throw new Error('The bookmarks response was not in the expected format.');
        if (active) setItems(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Bookmarks could not be loaded.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function removeBookmark(id: string) {
    setRemoving(id);
    setFeedback('');
    try {
      await api(`/api/v1/bookmarks/${encodeURIComponent(id)}`, { method: 'DELETE' });
      setItems((current) => current.filter((item) => item.id !== id));
      setFeedback('Bookmark removed.');
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : 'Bookmark could not be removed.');
    } finally {
      setRemoving('');
    }
  }

  return (
    <section className="page-content">
      <div className="page-heading">
        <p className="eyebrow">Keep useful material close</p>
        <h1>Bookmarks</h1>
        <p className="page-description">Questions and documents you have saved for another study session.</p>
      </div>

      {feedback && <p aria-live="polite" className="inline-feedback">{feedback}</p>}
      {error && <div className="inline-error" role="alert">{error}</div>}
      {loading ? (
        <div aria-label="Loading bookmarks" className="loading-list" role="status"><span /><span /><span /></div>
      ) : items.length === 0 && !error ? (
        <div className="state-card">
          <span className="state-symbol">◇</span>
          <strong>No bookmarks yet</strong>
          <p>Save a question from search to find it here later.</p>
          <Link className="button button-secondary" to="/search">Explore questions</Link>
        </div>
      ) : (
        <div className="result-list">
          <div className="result-list-header">
            <span>{items.length} saved {items.length === 1 ? 'item' : 'items'}</span>
            <span>Private to your library</span>
          </div>
          {items.map((item, index) => {
            const to = destination(item);
            return (
              <article className="question-result bookmark-result" key={item.id}>
                <div aria-hidden="true" className="result-index">{String(index + 1).padStart(2, '0')}</div>
                <div className="result-body">
                  <span className="bookmark-kind">{item.target_type}</span>
                  {to
                    ? <Link className="result-question" to={to}>Open saved {item.target_type}</Link>
                    : <strong className="result-question">Saved item type: {item.target_type}</strong>}
                  <div className="result-meta"><span>Reference {item.target_id}</span></div>
                </div>
                <button
                  className="button button-quiet remove-bookmark"
                  disabled={removing === item.id}
                  onClick={() => void removeBookmark(item.id)}
                  type="button"
                >
                  {removing === item.id ? 'Removing…' : 'Remove'}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
