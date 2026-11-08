import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

const FILE_TYPES: Record<string, string> = {
  '.pdf': 'application/pdf',
  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.tif': 'image/tiff',
  '.tiff': 'image/tiff',
  '.bmp': 'image/bmp',
};
const ACCEPT_EXTENSIONS = Object.keys(FILE_TYPES);
const DEFAULT_MAX_SIZE_MB = 10;

type UploadStatus = 'idle' | 'uploading' | 'queued' | 'processing' | 'quarantined' | 'completed' | 'failed';

function csrfTokenValue(): string {
  const entry = document.cookie.split('; ').find((part) => part.startsWith('ra_csrf='));
  return entry ? decodeURIComponent(entry.slice('ra_csrf='.length)) : '';
}

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [grade, setGrade] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [subjects, setSubjects] = useState<{ id: string; name: string }[]>([]);
  const [subjectId, setSubjectId] = useState('');
  const [subjectsError, setSubjectsError] = useState('');
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [documentId, setDocumentId] = useState('');
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [maxSizeMb, setMaxSizeMb] = useState(DEFAULT_MAX_SIZE_MB);
  const [noAnswersConfirmed, setNoAnswersConfirmed] = useState(false);
  const maxSizeBytes = maxSizeMb * 1024 * 1024;

  const mimeType = (() => {
    const name = file?.name?.toLowerCase() || '';
    const extension = name.slice(name.lastIndexOf('.'));
    return FILE_TYPES[extension] || '';
  })();

  useEffect(() => {
    const controller = new AbortController();
    api<{ id: string; name: string }[]>('/api/v1/taxonomy/subjects', { signal: controller.signal })
      .then((items) => {
        if (!Array.isArray(items)) throw new Error('The subject catalog was not in the expected format.');
        if (!controller.signal.aborted) {
          setSubjects(items);
          setSubjectsError('');
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setSubjectsError(reason instanceof Error ? reason.message : 'The subject catalog could not be loaded.');
        }
      });
    api<{ max_size_mb: number; extensions: string[] }>('/api/v1/uploads/limits', { signal: controller.signal })
      .then((limits) => {
        if (!Number.isInteger(limits.max_size_mb) || limits.max_size_mb < 1) {
          throw new Error('The upload limits response was invalid.');
        }
        if (!controller.signal.aborted) setMaxSizeMb(limits.max_size_mb);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Upload limits could not be loaded.');
        }
      });
    return () => controller.abort();
  }, []);

  function handleFile(event: FormEvent<HTMLInputElement>) {
    const selected = event.currentTarget.files?.[0] || null;
    setError('');
    if (!selected) return;
    const ext = selected.name.slice(selected.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPT_EXTENSIONS.includes(ext)) {
      setFile(null);
      setError('Choose a PDF, DOCX, PPTX, or supported image file.');
      return;
    }
    if (selected.size > maxSizeBytes) {
      setFile(null);
      setError(`File must not exceed ${maxSizeMb} MB.`);
      return;
    }
    setFile(selected);
    setTitle(selected.name.replace(/\.[^/.]+$/, '') || '');
  }

  async function startUpload() {
    if (!file) return;
    setError('');
    setStatus('uploading');
    setProgress(10);

    try {
      const initiated = await api<{
        document_id: string;
        upload_url: string;
      }>('/api/v1/uploads/initiate', {
        method: 'POST',
        body: JSON.stringify({
          filename: file.name,
          mime_type: mimeType,
          file_size: file.size,
          no_answers_confirmed: noAnswersConfirmed,
          title: title || file.name,
          grade: grade ? Number(grade) : null,
          academic_year: academicYear ? Number(academicYear) : null,
          subject_id: subjectId || null,
        }),
      });
      setDocumentId(initiated.document_id);
      setStatus('queued');
      setProgress(35);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(initiated.upload_url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRF-Token': csrfTokenValue(),
        },
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        throw new Error(text || 'The upload could not be completed.');
      }

      const completion = await response.json() as { status?: string; security_status?: string };
      if (completion.status === 'quarantined') {
        setStatus('quarantined');
        setProgress(100);
        setError('The upload is stored privately and is not being processed because the security scan could not clear it. An administrator must review or rescan it.');
        return;
      }
      setStatus('processing');
      setProgress(65);
      pollDocument(initiated.document_id);
    } catch (reason: unknown) {
      setStatus('failed');
      setError(reason instanceof Error ? reason.message : 'The upload could not be completed.');
    }
  }

  async function pollDocument(id: string) {
    let attempts = 0;
    const timer = setInterval(async () => {
      attempts += 1;
      try {
        const doc = await api<{ status: string; security_status?: string }>(`/api/v1/documents/${encodeURIComponent(id)}`);
        if (doc.security_status && doc.security_status !== 'clean') {
          setStatus('quarantined');
          clearInterval(timer);
          return;
        }
        if (doc.status === 'completed') {
          setStatus('completed');
          setProgress(100);
          clearInterval(timer);
        } else if (doc.status === 'failed') {
          setStatus('failed');
          clearInterval(timer);
        } else if (attempts > 40) {
          clearInterval(timer);
        }
      } catch {
        if (attempts > 10) clearInterval(timer);
      }
    }, 2000);
  }

  return (
    <section className="page-content">
      <nav aria-label="Breadcrumb" className="breadcrumbs">
        <Link to="/search">Search</Link><span>/</span><span>Upload</span>
      </nav>
      <div className="page-heading upload-heading">
        <p className="eyebrow">Add to the archive</p>
        <h1>Upload a document</h1>
        <p className="page-description">
          Upload a past test or worksheet (PDF, Office presentation, or image). Extracted questions are held for review before publication.
        </p>
      </div>

      {error && <p className="inline-error" role="alert">{error}</p>}

      <div className="auth-form card-surface upload-form">
        <label>
          <span className="form-label">Document file</span>
          <input
            accept={ACCEPT_EXTENSIONS.join(',')}
            onChange={(event) => void handleFile(event as unknown as FormEvent<HTMLInputElement>)}
            required
            type="file"
          />
          <span className="form-hint">
            PDF, DOCX, PPTX, PNG, JPEG, TIFF, BMP, or WebP — up to {maxSizeMb} MB. The source file is kept private and can be used to verify difficult extractions.
          </span>
        </label>
        <label className="upload-policy-confirmation">
          <input
            checked={noAnswersConfirmed}
            onChange={(event) => setNoAnswersConfirmed(event.target.checked)}
            type="checkbox"
          />
          <span>I confirm this upload does not contain answers or an answer key, and I have permission to share this material.</span>
        </label>
        <label>
          <span className="form-label">Title (optional)</span>
          <input
            autoComplete="off"
            onChange={(event) => setTitle(event.target.value)}
            placeholder={file?.name || 'Untitled document'}
            type="text"
            value={title}
          />
        </label>
        <div className="upload-metadata">
          <label>
            <span className="form-label">Subject (optional)</span>
            <select onChange={(event) => setSubjectId(event.target.value)} value={subjectId}>
              <option value="">Not specified</option>
              {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
            </select>
            {subjectsError && <span className="form-hint">{subjectsError}</span>}
          </label>
          <label>
            <span className="form-label">Grade (optional)</span>
            <select onChange={(event) => setGrade(event.target.value)} value={grade}>
              <option value="">Not specified</option>
              {[9, 10, 11, 12].map((value) => <option key={value} value={value}>Grade {value}</option>)}
            </select>
          </label>
          <label>
            <span className="form-label">Exam year (optional)</span>
            <input
              max="2100"
              min="1900"
              onChange={(event) => setAcademicYear(event.target.value)}
              placeholder="e.g. 2023"
              type="number"
              value={academicYear}
            />
          </label>
        </div>
        <div className="collection-form-row">
          <button
            className="button button-primary"
            disabled={!file || !noAnswersConfirmed || status === 'uploading'}
            onClick={() => void startUpload()}
            type="button"
          >
            {status === 'uploading' ? 'Uploading…' : 'Start upload'}
          </button>
        </div>
      </div>

      {documentId && (
        <div className="card-surface upload-status">
          <p className="paper-label">Upload status</p>
          <p>
            <strong>Document {documentId}</strong>{' '}
            <span className={`status-pill status-${status}`}>{status.replaceAll('_', ' ')}</span>
          </p>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${Math.min(progress, 100)}%` }} />
          </div>
          {status === 'completed' && (
            <p>
              Your document has been processed. Extracted questions remain unavailable until review.{' '}
              <Link to={`/documents/${documentId}`}>View document →</Link>
            </p>
          )}
          {status === 'failed' && (
            <p className="inline-error" role="alert">
              The upload failed. Please try again.
            </p>
          )}
        </div>
      )}
    </section>
  );
}