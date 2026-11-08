import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

type ReviewQuestion = {
  id: string;
  document_id: string;
  document_title: string | null;
  original_filename: string | null;
  source_download_url: string;
  source_page_url: string | null;
  page: number | null;
  text: string;
  question_type: string;
  quality_signals: {
    reasons?: string[];
    ocr_confidence?: number | null;
  } | null;
  content: {
    source_regions?: { text: string; bbox: number[]; confidence: number | null }[];
    source_ocr_text?: string;
    source_ocr_confidence?: number | null;
  } | null;
};

type QuarantinedDocument = {
  id: string;
  title: string | null;
  original_filename: string | null;
  security_status: 'infected' | 'unavailable';
  scan_detail: string | null;
  uploaded_at: string | null;
  source_url: string;
};

type ProcessingJob = {
  id: string;
  document_id: string;
  document_title: string | null;
  original_filename: string | null;
  job_type: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'held';
  attempt_count: number;
  available_at: string | null;
  error_category: string | null;
};

type DeletionRequest = {
  user_id: string;
  email: string | null;
  display_name: string | null;
  requested_at: string | null;
};

export default function Admin() {
  const [questions, setQuestions] = useState<ReviewQuestion[]>([]);
  const [quarantined, setQuarantined] = useState<QuarantinedDocument[]>([]);
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [deletionRequests, setDeletionRequests] = useState<DeletionRequest[]>([]);
  const [rejectionNotes, setRejectionNotes] = useState<Record<string, string>>({});
  const [deletionNotes, setDeletionNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [loadingError, setLoadingError] = useState('');
  const [savingId, setSavingId] = useState('');
  const [securityError, setSecurityError] = useState('');
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api<ReviewQuestion[]>('/api/v1/admin/question-review-queue', { signal: controller.signal }),
      api<QuarantinedDocument[]>('/api/v1/admin/security-quarantine', { signal: controller.signal }),
      api<ProcessingJob[]>('/api/v1/admin/jobs?limit=100', { signal: controller.signal }),
      api<DeletionRequest[]>('/api/v1/admin/deletion-requests', { signal: controller.signal }),
    ])
      .then(([items, quarantinedItems, processingJobs, deletionItems]) => {
        if (!Array.isArray(items) || !Array.isArray(quarantinedItems) || !Array.isArray(processingJobs) || !Array.isArray(deletionItems)) {
          throw new Error('An admin queue was not in the expected format.');
        }
        if (!controller.signal.aborted) {
          setQuestions(items);
          setQuarantined(quarantinedItems);
          setJobs(processingJobs);
          setDeletionRequests(deletionItems);
          setLoadingError('');
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setLoadingError(reason instanceof Error ? reason.message : 'The review queue could not be loaded.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function reviewDeletion(request: DeletionRequest, decision: 'approve' | 'reject') {
    setSavingId(request.user_id);
    setFeedback('');
    try {
      await api(`/api/v1/admin/deletion-requests/${encodeURIComponent(request.user_id)}/decision`, {
        method: 'POST',
        body: JSON.stringify({
          decision,
          note: deletionNotes[request.user_id]?.trim() ?? '',
        }),
      });
      setDeletionRequests((items) => items.filter((item) => item.user_id !== request.user_id));
      setFeedback(decision === 'approve'
        ? 'Account identifiers and private associations were removed; contribution records and source documents remain attributed to Deleted contributor.'
        : 'Deletion request rejected and the account reactivated.');
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : 'The deletion decision could not be saved.');
    } finally {
      setSavingId('');
    }
  }

  async function retryJob(job: ProcessingJob) {
    setSavingId(job.id);
    setFeedback('');
    try {
      await api(`/api/v1/admin/jobs/${encodeURIComponent(job.id)}/retry`, { method: 'POST' });
      setJobs((items) => items.map((item) => item.id === job.id
        ? { ...item, status: 'queued', attempt_count: 0, error_category: null }
        : item));
      setFeedback('Processing job queued for retry.');
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : 'The job could not be retried.');
    } finally {
      setSavingId('');
    }
  }

  async function reviewSecurity(document: QuarantinedDocument, decision: 'rescan' | 'reject') {
    setSavingId(document.id);
    setSecurityError('');
    try {
      if (decision === 'rescan') {
        const result = await api<{ security_status: string }>(
          `/api/v1/admin/documents/${encodeURIComponent(document.id)}/security-rescan`,
          { method: 'POST' },
        );
        if (result.security_status === 'clean') {
          setQuarantined((items) => items.filter((item) => item.id !== document.id));
          setFeedback('File scanned clean and queued for extraction.');
        } else {
          setFeedback('Threat still detected. The file remains quarantined.');
        }
      } else {
        const note = rejectionNotes[document.id]?.trim() ?? '';
        await api(`/api/v1/admin/documents/${encodeURIComponent(document.id)}/security-reject`, {
          method: 'POST',
          body: JSON.stringify({ note }),
        });
        setQuarantined((items) => items.filter((item) => item.id !== document.id));
        setFeedback('Upload rejected. The decision and rationale were recorded.');
      }
    } catch (reason) {
      setSecurityError(reason instanceof Error ? reason.message : 'The security decision could not be completed.');
    } finally {
      setSavingId('');
    }
  }

  async function review(question: ReviewQuestion, decision: 'approve' | 'reject') {
    setSavingId(question.id);
    setFeedback('');
    try {
      const params = new URLSearchParams({ decision });
      await api(`/api/v1/questions/${encodeURIComponent(question.id)}/review?${params}`, { method: 'POST' });
      setQuestions((items) => items.filter((item) => item.id !== question.id));
      setFeedback(decision === 'approve' ? 'Question approved for publication.' : 'Question rejected and removed from the queue.');
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : 'The review decision could not be saved.');
    } finally {
      setSavingId('');
    }
  }

  return (
    <section className="page-content admin-review-page">
      <div className="page-heading">
        <p className="eyebrow">Recall Atlas operations</p>
        <h1>Question review</h1>
        <p className="page-description">Check extracted text against its private source before approving a question for publication.</p>
      </div>

      <section aria-labelledby="security-quarantine-heading">
        <h2 id="security-quarantine-heading">Security quarantine</h2>
        <p className="page-description">Files here were detected as unsafe or could not be scanned. Rescanning is the only way to release a file; rejection requires a rationale.</p>
        {securityError && <p className="inline-error" role="alert">{securityError}</p>}
        {quarantined.length === 0 ? (
          <div className="state-card compact-state"><strong>No quarantined uploads</strong></div>
        ) : (
          <div className="admin-review-list">
            {quarantined.map((document) => (
              <article className="question-paper admin-review-item" key={document.id}>
                <div className="admin-review-meta">
                  <span className="status-pill">{document.security_status === 'infected' ? 'Threat detected' : 'Scanner unavailable'}</span>
                  <span>{document.scan_detail?.replaceAll('_', ' ')}</span>
                  <strong>{document.title || document.original_filename || 'Uploaded document'}</strong>
                </div>
                <div className="admin-review-actions">
                  <a className="button button-secondary" href={document.source_url}>Download quarantined original</a>
                  <button
                    className="button button-secondary"
                    disabled={savingId === document.id}
                    onClick={() => void reviewSecurity(document, 'rescan')}
                    type="button"
                  >
                    {savingId === document.id ? 'Scanning…' : 'Rescan and release if clean'}
                  </button>
                </div>
                <label>
                  <span className="form-label">Rejection rationale</span>
                  <textarea
                    maxLength={1000}
                    minLength={4}
                    onChange={(event) => setRejectionNotes((notes) => ({ ...notes, [document.id]: event.target.value }))}
                    value={rejectionNotes[document.id] ?? ''}
                  />
                </label>
                <button
                  className="button button-secondary"
                  disabled={savingId === document.id || (rejectionNotes[document.id]?.trim().length ?? 0) < 4}
                  onClick={() => void reviewSecurity(document, 'reject')}
                  type="button"
                >
                  Reject quarantined upload
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="account-deletion-heading">
        <h2 id="account-deletion-heading">Account deletion requests</h2>
        <p className="page-description">Approval removes profile identifiers, sessions, private collections, bookmarks, notifications, and auth tokens. Contribution records and source documents are retained under “Deleted contributor”; obtain legal approval for this retention policy before processing requests.</p>
        {deletionRequests.length === 0 ? (
          <div className="state-card compact-state"><strong>No pending deletion requests</strong></div>
        ) : (
          <div className="admin-review-list">
            {deletionRequests.map((request) => (
              <article className="question-paper admin-review-item" key={request.user_id}>
                <div className="admin-review-meta">
                  <strong>{request.display_name || 'Account holder'}</strong>
                  <span>{request.email}</span>
                  <span>Requested {request.requested_at ? new Date(request.requested_at).toLocaleString() : 'date unavailable'}</span>
                </div>
                <label>
                  <span className="form-label">Review rationale</span>
                  <textarea
                    maxLength={1000}
                    minLength={4}
                    onChange={(event) => setDeletionNotes((notes) => ({ ...notes, [request.user_id]: event.target.value }))}
                    value={deletionNotes[request.user_id] ?? ''}
                  />
                </label>
                <div className="admin-review-actions">
                  <button
                    className="button button-secondary"
                    disabled={savingId === request.user_id || (deletionNotes[request.user_id]?.trim().length ?? 0) < 4}
                    onClick={() => void reviewDeletion(request, 'reject')}
                    type="button"
                  >
                    Reject request
                  </button>
                  <button
                    className="button button-primary"
                    disabled={savingId === request.user_id || (deletionNotes[request.user_id]?.trim().length ?? 0) < 4}
                    onClick={() => void reviewDeletion(request, 'approve')}
                    type="button"
                  >
                    {savingId === request.user_id ? 'Processing…' : 'Approve deletion'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="processing-jobs-heading">
        <h2 id="processing-jobs-heading">Processing jobs</h2>
        <p className="page-description">Jobs are persisted in the database and processed by the separately deployed worker. Failed jobs retry automatically up to the configured attempt limit.</p>
        {jobs.length === 0 ? (
          <div className="state-card compact-state"><strong>No processing jobs</strong></div>
        ) : (
          <div className="admin-review-list">
            {jobs.map((job) => (
              <article className="question-paper admin-review-item" key={job.id}>
                <div className="admin-review-meta">
                  <span className="status-pill">{job.status}</span>
                  <span>{job.job_type.replaceAll('_', ' ')}</span>
                  <Link to={`/documents/${job.document_id}`}>{job.document_title || job.original_filename || 'Uploaded document'}</Link>
                  <span>Attempts: {job.attempt_count}</span>
                </div>
                {job.error_category && <p className="admin-review-reasons">Last error: {job.error_category}</p>}
                {job.status === 'failed' && (
                  <button
                    className="button button-secondary"
                    disabled={savingId === job.id}
                    onClick={() => void retryJob(job)}
                    type="button"
                  >
                    {savingId === job.id ? 'Queueing…' : 'Retry job'}
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {loadingError && <div className="state-card state-error" role="alert"><strong>Review queue unavailable</strong><p>{loadingError}</p></div>}
      {feedback && <p aria-live="polite" className="inline-feedback" role="status">{feedback}</p>}
      {loading ? (
        <div aria-label="Loading review queue" className="loading-list" role="status"><span /><span /><span /></div>
      ) : !loadingError && questions.length === 0 ? (
        <div className="state-card compact-state"><strong>Nothing to review</strong><p>New extracted questions will appear here.</p></div>
      ) : (
        <div className="admin-review-list">
          {questions.map((question) => (
            <article className="question-paper admin-review-item" key={question.id}>
              <div className="admin-review-meta">
                <span className="status-pill">{question.question_type.replaceAll('_', ' ')}</span>
                <span>{question.page ? `Source page ${question.page}` : 'Page not listed'}</span>
                <Link to={`/documents/${question.document_id}`}>{question.document_title || question.original_filename || 'Source document'}</Link>
              </div>
              <pre className="admin-review-text">{question.text}</pre>
              {question.quality_signals?.reasons?.length ? (
                <p className="admin-review-reasons">Review notes: {question.quality_signals.reasons.join(', ')}</p>
              ) : null}
              {question.content?.source_regions?.length ? (
                <details className="admin-review-reasons">
                  <summary>OCR source locations ({question.content.source_regions.length})</summary>
                  <ul>
                    {question.content.source_regions.map((region, index) => (
                      <li key={`${region.text}-${index}`}>
                        “{region.text}” — normalized box [{region.bbox.map((value) => value.toFixed(3)).join(', ')}]
                      </li>
                    ))}
                  </ul>
                  <p>Coordinates are normalized to the OCR page image and are provenance hints, not verified crops.</p>
                </details>
              ) : null}
              {question.content?.source_ocr_text && (
                <details className="admin-review-reasons">
                  <summary>
                    Unverified OCR alternative
                    {question.content.source_ocr_confidence != null
                      ? ` (${(question.content.source_ocr_confidence * 100).toFixed(0)}% confidence)`
                      : ''}
                  </summary>
                  <pre className="admin-review-text">{question.content.source_ocr_text}</pre>
                  <p>This OCR pass may misread mathematical notation. Compare it with the original PDF before approving.</p>
                </details>
              )}
              {question.source_page_url && (
                <figure className="admin-source-preview">
                  <img alt={`Original source page ${question.page}`} loading="lazy" src={question.source_page_url} />
                  <figcaption>Original source page for comparison</figcaption>
                </figure>
              )}
              <div className="admin-review-actions">
                <a className="button button-secondary" href={question.source_download_url}>Download original</a>
                <button
                  className="button button-secondary"
                  disabled={savingId === question.id}
                  onClick={() => void review(question, 'reject')}
                  type="button"
                >
                  Reject
                </button>
                <button
                  className="button button-primary"
                  disabled={savingId === question.id}
                  onClick={() => void review(question, 'approve')}
                  type="button"
                >
                  {savingId === question.id ? 'Saving…' : 'Approve'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
