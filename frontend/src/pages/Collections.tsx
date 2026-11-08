import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

type Collection = { id: string; name: string; item_count: number };
type CollectionItem = { id: string; question_id: string; page: number | null; text: string; question_type: string };

async function getCollections(): Promise<Collection[]> {
  const result = await api<Collection[]>('/api/v1/collections');
  if (!Array.isArray(result)) throw new Error('The collections response was not in the expected format.');
  return result;
}

export default function Collections() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [expandedId, setExpandedId] = useState('');
  const [items, setItems] = useState<CollectionItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);

  useEffect(() => {
    let active = true;
    getCollections()
      .then((result) => { if (active) setCollections(result); })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Collections could not be loaded.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function createCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanName = name.trim();
    if (!cleanName) {
      setError('Enter a name for your collection.');
      return;
    }
    setCreating(true);
    setError('');
    setMessage('');
    try {
      await api('/api/v1/collections', {
        method: 'POST',
        body: JSON.stringify({ name: cleanName }),
      });
      setName('');
      setMessage('Collection created.');
      setLoading(true);
      try {
        setCollections(await getCollections());
      } catch (reason) {
        setError(`Collection created, but the list could not be refreshed: ${reason instanceof Error ? reason.message : 'unknown error'}`);
      }
      setLoading(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The collection could not be created.');
    } finally {
      setLoading(false);
      setCreating(false);
    }
  }

  async function toggleCollection(collectionId: string) {
    if (expandedId === collectionId) {
      setExpandedId('');
      setItems([]);
      return;
    }
    setExpandedId(collectionId);
    setItems([]);
    setItemsLoading(true);
    setError('');
    try {
      const result = await api<CollectionItem[]>(`/api/v1/collections/${encodeURIComponent(collectionId)}/items`);
      if (!Array.isArray(result)) throw new Error('The collection items response was not in the expected format.');
      setItems(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Collection items could not be loaded.');
    } finally {
      setItemsLoading(false);
    }
  }

  async function removeItem(item: CollectionItem) {
    if (!expandedId) return;
    try {
      await api(`/api/v1/collections/${encodeURIComponent(expandedId)}/items/${encodeURIComponent(item.id)}`, { method: 'DELETE' });
      setItems((current) => current.filter((entry) => entry.id !== item.id));
      setCollections((current) => current.map((collection) => collection.id === expandedId
        ? { ...collection, item_count: Math.max(0, collection.item_count - 1) }
        : collection));
      setMessage('Question removed from collection.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The question could not be removed.');
    }
  }

  return (
    <section className="page-content">
      <div className="page-heading collections-heading">
        <div>
          <p className="eyebrow">Your private study space</p>
          <h1>Collections</h1>
          <p className="page-description">Group useful questions into sets you can return to.</p>
        </div>
        <span aria-hidden="true" className="heading-stamp">RA<br /><small>LIBRARY</small></span>
      </div>

      <form className="create-collection card-surface" onSubmit={(event) => void createCollection(event)}>
        <label htmlFor="collection-name">
          <span className="form-label">Create a collection</span>
          <span className="form-hint">Give a study set a name that makes sense to you.</span>
        </label>
        <div className="collection-form-row">
          <input
            autoComplete="off"
            id="collection-name"
            maxLength={80}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Biology — cell structure"
            value={name}
          />
          <button className="button button-primary" disabled={creating || !name.trim()} type="submit">
            {creating ? 'Creating…' : 'New collection'} <span aria-hidden="true">+</span>
          </button>
        </div>
      </form>

      {error && <div className="inline-error" role="alert">{error}</div>}
      {message && <p aria-live="polite" className="inline-feedback">{message}</p>}

      <div className="section-heading collection-list-heading">
        <div><p className="eyebrow">Saved sets</p><h2>Your collections</h2></div>
        {!loading && <span className="quiet-count">{collections.length}</span>}
      </div>

      {loading ? (
        <div aria-label="Loading collections" className="loading-list" role="status"><span /><span /><span /></div>
      ) : collections.length === 0 && !error ? (
        <div className="state-card">
          <span className="state-symbol">▤</span>
          <strong>Your library starts here</strong>
          <p>Create a collection, then save questions as you search.</p>
          <Link className="button button-secondary" to="/search">Search questions</Link>
        </div>
      ) : (
        <div className="collection-grid">
          {collections.map((collection, index) => (
            <article className="collection-card" key={collection.id}>
              <span aria-hidden="true" className={`collection-art collection-art-${index % 3}`}>
                <i /><i /><i />
                <small>{String(index + 1).padStart(2, '0')}</small>
              </span>
              <div className="collection-card-copy">
                <h3>{collection.name}</h3>
                <p>{collection.item_count} {collection.item_count === 1 ? 'question' : 'questions'}</p>
              </div>
              <button
                aria-expanded={expandedId === collection.id}
                className="text-link"
                onClick={() => void toggleCollection(collection.id)}
                type="button"
              >
                {expandedId === collection.id ? 'Hide' : 'Open'}
              </button>
              {expandedId === collection.id && (
                <div className="collection-items">
                  {itemsLoading ? <p role="status">Loading questions…</p> : items.length === 0 ? <p>No saved questions in this collection.</p> : items.map((item) => (
                    <article className="collection-item" key={item.id}>
                      <Link to={`/questions/${item.question_id}`}>{item.text}</Link>
                      <span>{item.page ? `Page ${item.page}` : 'Page not listed'}</span>
                      <button className="text-link" onClick={() => void removeItem(item)} type="button">Remove</button>
                    </article>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
