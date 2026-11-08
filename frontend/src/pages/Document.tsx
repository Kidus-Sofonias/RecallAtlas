import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';

type DocumentRecord = {
  id: string;
  status: string;
  mime_type: string;
  page_count: number | null;
  title: string | null;
  grade: number | null;
  academic_year: number | null;
  created_at: string | null;
};

type DocumentQuestion = {
  id: string;
  page: number | null;
  text: string;
  quality: string;
  content: { page_context?: string } | null;
};

export default function Document() {
  const { id = '' } = useParams();
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get('q') || '';
  const searchPath = searchQuery ? `/search?q=${encodeURIComponent(searchQuery)}` : '/search';
  const [documentState, setDocumentState] = useState<{
    id: string;
    document: DocumentRecord | null;
    questions: DocumentQuestion[];
    error: string;
  }>({ id: '', document: null, questions: [], error: '' });

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api<DocumentRecord>(`/api/v1/documents/${encodeURIComponent(id)}`, { signal: controller.signal }),
      api<DocumentQuestion[]>(`/api/v1/documents/${encodeURIComponent(id)}/questions`, { signal: controller.signal }),
    ])
      .then(([record, extracted]) => {
        if (!controller.signal.aborted) {
          setDocumentState({
            id,
            document: record,
            questions: Array.isArray(extracted) ? extracted : [],
            error: '',
          });
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setDocumentState({
            id,
            document: null,
            questions: [],
            error: reason instanceof Error ? reason.message : 'The document could not be loaded.',
          });
        }
      });
    return () => controller.abort();
  }, [id]);

  const loading = documentState.id !== id;
  const error = loading ? '' : documentState.error;
  const document = loading ? null : documentState.document;
  const questions = loading ? [] : documentState.questions;
  if (loading) return <div className="page-content"><div aria-label="Loading document" className="loading-list" role="status"><span /><span /><span /></div></div>;
  if (error) return <div className="page-content"><div className="state-card state-error" role="alert"><strong>Document unavailable</strong><p>{error}</p><Link className="text-link" to={searchPath}>Back to search →</Link></div></div>;
  if (!document) return null;

  return (
    <section className="page-content">
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <Link to={searchPath}>Search</Link><span>/</span><span>Source document</span>
      </nav>
      <div className="page-heading document-heading">
        <p className="eyebrow">Archive source</p>
        <h1>{document.title || 'Source document'}</h1>
        <p className="page-description">
          {[document.grade ? `Grade ${document.grade}` : null, document.academic_year, document.id]
            .filter(Boolean)
            .join(' · ')}
        </p>
      </div>

      <div className="document-overview">
        <div aria-hidden="true" className="document-glyph"><span>PDF</span><i /></div>
        <div className="document-facts">
          <span className="paper-label">PROCESSING STATUS</span>
          <strong className="status-pill">{document.status.replaceAll('_', ' ')}</strong>
          <p>{document.page_count === null ? 'Page count not available' : `${document.page_count} ${document.page_count === 1 ? 'page' : 'pages'}`}</p>
        </div>
        <div className="document-access-note">
          <strong>Original source</strong>
          <p>The original file is available to its uploader, administrators, and registered readers when this document has published questions.</p>
          <a className="text-link" href={`/api/v1/documents/${encodeURIComponent(document.id)}/source`}>Download original <span aria-hidden="true">↓</span></a>
        </div>
      </div>

      {document.mime_type === 'application/pdf' && document.status === 'completed' ? (
        <section aria-label="Original PDF reader" className="document-pdf-reader">
          <div className="document-pdf-toolbar">
            <strong>Original PDF</strong>
            <a className="button button-secondary" href={`/api/v1/documents/${encodeURIComponent(document.id)}/source`}>
              Download PDF <span aria-hidden="true">↓</span>
            </a>
          </div>
          <iframe
            loading="lazy"
            src={`/api/v1/documents/${encodeURIComponent(document.id)}/preview`}
            title={`Original PDF: ${document.title || 'source document'}`}
          />
        </section>
      ) : document.page_count && document.status === 'completed' ? (
        <details className="document-source-preview">
          <summary>Show source page 1</summary>
          <img
            alt="Original document, page 1"
            loading="lazy"
            src={`/api/v1/documents/${encodeURIComponent(document.id)}/pages/1`}
          />
        </details>
      ) : null}

      <div className="section-heading">
        <div><p className="eyebrow">Extraction record</p><h2>Questions from this document</h2></div>
        <span className="quiet-count">{questions.length}</span>
      </div>
      {questions.length === 0 ? (
        <div className="state-card compact-state">
          <strong>No extracted questions are available</strong>
          <p>Questions will appear here when the document has been processed.</p>
        </div>
      ) : (
        <div className="result-list document-question-list">
          {questions.map((question, index) => (
            <article className="question-result" key={question.id}>
              <div aria-hidden="true" className="result-index">{String(index + 1).padStart(2, '0')}</div>
              <div className="result-body">
                {question.content?.page_context && (
                  <p className="question-page-context">{question.content.page_context}</p>
                )}
                <Link className="result-question" to={`/questions/${question.id}${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`}>{question.text || 'Open extracted question'}</Link>
                <div className="result-meta">
                  <span>{question.page ? `Page ${question.page}` : 'Page not listed'}</span>
                  <span>·</span>
                  <span>{question.quality.replaceAll('_', ' ')}</span>
                </div>
              </div>
              <Link aria-label="Open question" className="result-arrow" to={`/questions/${question.id}${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`}>↗</Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
