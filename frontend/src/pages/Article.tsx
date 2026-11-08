import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';

type ArticleRecord = {
  id: string;
  title: string;
  summary: string;
  body: string;
  subject_id: string | null;
  created_at: string | null;
};

export default function Article() {
  const { id = '' } = useParams();
  const [state, setState] = useState<{ id: string; article: ArticleRecord | null; error: string }>({
    id: '',
    article: null,
    error: '',
  });

  useEffect(() => {
    const controller = new AbortController();
    api<ArticleRecord>(`/api/v1/resources/${encodeURIComponent(id)}`, { signal: controller.signal })
      .then((article) => {
        if (!controller.signal.aborted) setState({ id, article, error: '' });
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setState({
            id,
            article: null,
            error: reason instanceof Error ? reason.message : 'The article could not be loaded.',
          });
        }
      });
    return () => controller.abort();
  }, [id]);

  if (state.id !== id) {
    return <div className="page-content"><div aria-label="Loading article" className="loading-list" role="status"><span /><span /></div></div>;
  }
  if (state.error || !state.article) {
    return (
      <section className="page-content">
        <div className="state-card state-error" role="alert">
          <strong>Article unavailable</strong>
          <p>{state.error || 'This article could not be found.'}</p>
          <Link className="text-link" to="/search">Back to Explore →</Link>
        </div>
      </section>
    );
  }

  return (
    <article className="page-content article-page">
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <Link to="/search">Explore</Link><span>/</span><span>Article</span>
      </nav>
      <header className="page-heading">
        <p className="eyebrow">Study guide · {state.article.created_at ? new Date(state.article.created_at).toLocaleDateString() : 'Recall Atlas'}</p>
        <h1>{state.article.title}</h1>
        <p className="page-description">{state.article.summary}</p>
      </header>
      <div className="card-surface article-body">{state.article.body}</div>
      <p className="auth-switch"><Link to="/search">← Back to Explore</Link></p>
    </article>
  );
}
