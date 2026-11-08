import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAccountPrompt } from '../accountPromptContext';
import { useAuth } from '../authContext';

type QuestionRecord = {
  id: string;
  document_id: string;
  page: number | null;
  text: string;
  quality: string;
  content: { page_context?: string } | null;
};

type DocumentRecord = {
  id: string;
  title: string | null;
  grade: number | null;
  academic_year: number | null;
};

type Bookmark = { id: string; target_type: string; target_id: string };
type CommentRecord = { id: string; author_name: string; body: string; parent_comment_id: string | null };
type CollectionRecord = { id: string; name: string };

export default function Question() {
  const { id = '' } = useParams();
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get('q') || '';
  const searchPath = searchQuery ? `/search?q=${encodeURIComponent(searchQuery)}` : '/search';
  const [questionState, setQuestionState] = useState<{
    id: string;
    value: QuestionRecord | null;
    error: string;
  }>({ id: '', value: null, error: '' });
  const [sourceState, setSourceState] = useState<{
    id: string;
    value: DocumentRecord | null;
    error: string;
  }>({ id: '', value: null, error: '' });
  const [bookmarkId, setBookmarkId] = useState('');
  const [comments, setComments] = useState<CommentRecord[]>([]);
  const [commentDraft, setCommentDraft] = useState('');
  const [replyTo, setReplyTo] = useState('');
  const [collectionList, setCollectionList] = useState<CollectionRecord[]>([]);
  const [selectedCollection, setSelectedCollection] = useState('');
  const [collectionFeedback, setCollectionFeedback] = useState('');
  const [feedback, setFeedback] = useState('');
  const [saving, setSaving] = useState(false);
  const { recordView } = useAccountPrompt();
  const { user } = useAuth();

  useEffect(() => {
    const controller = new AbortController();
    api<QuestionRecord>(`/api/v1/questions/${encodeURIComponent(id)}`, { signal: controller.signal })
      .then((value) => {
        if (!controller.signal.aborted) {
          setQuestionState({ id, value, error: '' });
          setSourceState({ id, value: null, error: '' });
          recordView();
          api<DocumentRecord>(`/api/v1/documents/${encodeURIComponent(value.document_id)}`, { signal: controller.signal })
            .then((document) => {
              if (!controller.signal.aborted) setSourceState({ id, value: document, error: '' });
            })
            .catch((reason: unknown) => {
              if (reason instanceof DOMException && reason.name === 'AbortError') return;
              if (!controller.signal.aborted) {
                setSourceState({
                  id,
                  value: null,
                  error: reason instanceof Error ? reason.message : 'Source details could not be loaded.',
                });
              }
            });
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setQuestionState({
            id,
            value: null,
            error: reason instanceof Error ? reason.message : 'The question could not be loaded.',
          });
        }
      });

    let active = true;
    api<Bookmark[]>('/api/v1/bookmarks')
      .then((items) => {
        if (!active || !Array.isArray(items)) return;
        setBookmarkId(items.find((item) => item.target_type === 'question' && item.target_id === id)?.id || '');
      })
      .catch(() => {
        if (active) setFeedback('Bookmark status is unavailable right now.');
      });

    return () => {
      controller.abort();
      active = false;
    };
  }, [id, recordView]);

  useEffect(() => {
    if (!user || questionState.id !== id || !questionState.value) return;
    const params = new URLSearchParams({ target_type: 'question', target_id: id });
    const controller = new AbortController();
    api<CommentRecord[]>(`/api/v1/comments?${params}`, { signal: controller.signal })
      .then((items) => {
        if (!Array.isArray(items)) throw new Error('Comments were not in the expected format.');
        if (!controller.signal.aborted) setComments(items);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setFeedback(reason instanceof Error ? reason.message : 'Comments could not be loaded.');
        }
      });
    api<CollectionRecord[]>('/api/v1/collections', { signal: controller.signal })
      .then((items) => {
        if (Array.isArray(items) && !controller.signal.aborted) setCollectionList(items);
      })
      .catch(() => {
        if (!controller.signal.aborted) setCollectionList([]);
      });
    return () => controller.abort();
  }, [id, questionState.id, questionState.value, user]);

  async function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const body = commentDraft.trim();
    if (!body) return;
    try {
      await api('/api/v1/comments', {
        method: 'POST',
        body: JSON.stringify({
          target_type: 'question',
          target_id: id,
          body,
          parent_comment_id: replyTo || null,
        }),
      });
      setCommentDraft('');
      setReplyTo('');
      const params = new URLSearchParams({ target_type: 'question', target_id: id });
      setComments(await api<CommentRecord[]>(`/api/v1/comments?${params}`));
      setFeedback('Comment posted.');
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : 'Comment could not be posted.');
    }
  }

  async function addToCollection() {
    if (!selectedCollection) return;
    setCollectionFeedback('');
    try {
      await api(`/api/v1/collections/${encodeURIComponent(selectedCollection)}/items?question_id=${encodeURIComponent(id)}`, { method: 'POST' });
      setCollectionFeedback('Added to your collection.');
    } catch (reason) {
      setCollectionFeedback(reason instanceof Error ? reason.message : 'Question could not be added.');
    }
  }

  async function toggleBookmark() {
    setSaving(true);
    setFeedback('');
    try {
      if (bookmarkId) {
        await api(`/api/v1/bookmarks/${bookmarkId}`, { method: 'DELETE' });
        setBookmarkId('');
        setFeedback('Removed from bookmarks.');
      } else {
        const params = new URLSearchParams({ target_type: 'question', target_id: id });
        const result = await api<{ id: string }>(`/api/v1/bookmarks?${params}`, { method: 'POST' });
        setBookmarkId(result.id);
        setFeedback('Saved to bookmarks.');
      }
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : 'Bookmark could not be updated.');
    } finally {
      setSaving(false);
    }
  }

  const loading = questionState.id !== id;
  const error = loading ? '' : questionState.error;
  const question = loading ? null : questionState.value;
  const source = sourceState.id === id ? sourceState.value : null;
  const sourceError = sourceState.id === id ? sourceState.error : '';
  if (loading) return <div className="page-content"><div aria-label="Loading question" className="loading-list" role="status"><span /><span /><span /></div></div>;
  if (error) return <div className="page-content"><div className="state-card state-error" role="alert"><strong>Question unavailable</strong><p>{error}</p><Link className="text-link" to={searchPath}>Back to search →</Link></div></div>;
  if (!question) return null;

  return (
    <article className="page-content reading-page">
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <Link to={searchPath}>Search</Link><span>/</span><span>Question</span>
      </nav>
      <header className="reading-header">
        <div>
          <p className="eyebrow">Question archive <span className="eyebrow-dot" /></p>
          <h1>Question</h1>
        </div>
        <button
          aria-pressed={Boolean(bookmarkId)}
          className={`button button-secondary ${bookmarkId ? 'button-saved' : ''}`}
          disabled={saving}
          onClick={() => void toggleBookmark()}
          type="button"
        >
          <span aria-hidden="true">{bookmarkId ? '◆' : '◇'}</span>
          {bookmarkId ? 'Saved' : 'Save question'}
        </button>
      </header>
      {user && collectionList.length > 0 && (
        <div className="question-collection-action">
          <label>
            <span className="sr-only">Choose a collection</span>
            <select onChange={(event) => setSelectedCollection(event.target.value)} value={selectedCollection}>
              <option value="">Add to collection…</option>
              {collectionList.map((collection) => <option key={collection.id} value={collection.id}>{collection.name}</option>)}
            </select>
          </label>
          <button className="button button-secondary" disabled={!selectedCollection} onClick={() => void addToCollection()} type="button">Add</button>
          {collectionFeedback && <span aria-live="polite" role="status">{collectionFeedback}</span>}
        </div>
      )}

      <div className="reading-meta">
        <span className="status-pill">{question.quality.replaceAll('_', ' ')}</span>
      </div>

      <section aria-label="Question text" className="question-paper">
        <span className="paper-label">QUESTION</span>
        {question.content?.page_context && (
          <p className="question-page-context">{question.content.page_context}</p>
        )}
        <div className="question-text">{question.text}</div>
      </section>

      {feedback && <p aria-live="polite" className="inline-feedback">{feedback}</p>}

      <section aria-label="Original source" className="source-panel">
        <div className="source-icon" aria-hidden="true">↗</div>
        <div className="source-details">
          <span className="paper-label">ORIGINAL SOURCE</span>
          <strong>{source?.title || 'Source document'}</strong>
          <p aria-live="polite" className={sourceError ? 'source-error' : ''} role="status">
            {[question.page ? `Page ${question.page}` : 'Page not listed', source?.grade ? `Grade ${source.grade}` : null, source?.academic_year, sourceError ? `Source details unavailable: ${sourceError}` : null]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <Link aria-label="Open source document details" className="source-open" to={`/documents/${question.document_id}${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`}>View details <span aria-hidden="true">→</span></Link>
      </section>
      {question.page && (
        <details className="document-source-preview">
          <summary>Compare with original page {question.page}</summary>
          <img
            alt={`Original source page ${question.page}`}
            loading="lazy"
            src={`/api/v1/documents/${encodeURIComponent(question.document_id)}/pages/${question.page}`}
          />
        </details>
      )}
      <section aria-labelledby="question-comments-title" className="question-comments">
        <div className="section-heading">
          <div><p className="eyebrow">Community</p><h2 id="question-comments-title">Comments</h2></div>
          <span className="quiet-count">{comments.length}</span>
        </div>
        {!user ? (
          <p> <Link className="text-link" to="/login">Sign in</Link> to read and add comments.</p>
        ) : (
          <>
            <form className="question-comment-form" onSubmit={(event) => void submitComment(event)}>
              {replyTo && <p>Replying to a comment <button className="text-link" onClick={() => setReplyTo('')} type="button">Cancel</button></p>}
              <label className="sr-only" htmlFor="question-comment">Write a comment about this question</label>
              <textarea
                id="question-comment"
                maxLength={2000}
                onChange={(event) => setCommentDraft(event.target.value)}
                placeholder="Report a transcription issue or add a helpful note…"
                value={commentDraft}
              />
              <button className="button button-primary" disabled={!commentDraft.trim()} type="submit">Post comment</button>
            </form>
            <div className="question-comment-list">
              {comments.map((comment) => (
                <article className={`question-comment ${comment.parent_comment_id ? 'question-comment-reply' : ''}`} key={comment.id}>
                  <strong>{comment.author_name}</strong>
                  <p>{comment.body}</p>
                  <button className="text-link" onClick={() => setReplyTo(comment.id)} type="button">Reply</button>
                </article>
              ))}
              {comments.length === 0 && <p>No comments yet. Use a comment to flag a possible extraction issue.</p>}
            </div>
          </>
        )}
      </section>
    </article>
  );
}
