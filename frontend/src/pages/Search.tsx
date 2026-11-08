import { useEffect, useMemo, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../authContext';

type QuestionResult = {
  id: string;
  document_id: string;
  page: number | null;
  snippet: string;
  title: string;
  grade: number | null;
  academic_year: number | null;
  subject_id: string | null;
  subject: string | null;
};

type PaperResult = {
  id: string;
  title: string;
  grade: number | null;
  academic_year: number | null;
  subject_id: string | null;
  subject: string | null;
  posted_at: string | null;
};

type ArticleResult = {
  id: string;
  title: string;
  summary: string;
  subject_id: string | null;
  subject: string | null;
  posted_at: string | null;
};

type ExploreResults = {
  questions: QuestionResult[];
  papers: PaperResult[];
  articles: ArticleResult[];
};

type Suggestion = {
  type: 'question' | 'paper' | 'article';
  id: string;
  label: string;
  detail: string;
  href: string;
};

type Subject = {
  id: string;
  name: string;
};

type Bookmark = {
  id: string;
  target_type: string;
  target_id: string;
};

type ExploreTab = 'all' | 'questions' | 'papers' | 'articles';

const TAB_OPTIONS: { id: ExploreTab; label: string }[] = [
  { id: 'all', label: 'Explore' },
  { id: 'questions', label: 'Questions' },
  { id: 'papers', label: 'Past papers' },
  { id: 'articles', label: 'Articles' },
];
const NO_SUBJECT_PREFERENCES: string[] = [];

function parseExploreResults(data: unknown): ExploreResults {
  if (!data || typeof data !== 'object') throw new Error('Search results were not in the expected format.');
  const result = data as Record<string, unknown>;
  if (!Array.isArray(result.questions) || !Array.isArray(result.papers) || !Array.isArray(result.articles)) {
    throw new Error('Search results were not in the expected format.');
  }
  return result as ExploreResults;
}

function postedDate(value: string | null): string {
  if (!value) return 'Recently added';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Recently added';
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
}

function SearchResultQuestion({
  result,
  index,
  bookmarkId,
  saving,
  onBookmark,
}: {
  result: QuestionResult;
  index: number;
  bookmarkId?: string;
  saving: boolean;
  onBookmark: () => void;
}) {
  return (
    <article className="question-result">
      <div aria-hidden="true" className="result-index">{String(index + 1).padStart(2, '0')}</div>
      <div className="result-body">
        <Link className="result-question" to={`/questions/${result.id}`}>{result.snippet || 'Open question details'}</Link>
        <div className="result-meta">
          <Link to={`/documents/${result.document_id}`}>{result.title}</Link>
          {result.grade && <><span>·</span><span>Grade {result.grade}</span></>}
          {result.subject && <><span>·</span><span>{result.subject}</span></>}
          {result.academic_year && <><span>·</span><span>{result.academic_year}</span></>}
          {result.page && <><span>·</span><span>Page {result.page}</span></>}
        </div>
      </div>
      <button
        aria-label={bookmarkId ? 'Remove bookmark' : 'Bookmark question'}
        className={`icon-button ${bookmarkId ? 'is-saved' : ''}`}
        disabled={saving}
        onClick={onBookmark}
        title={bookmarkId ? 'Remove bookmark' : 'Save question'}
        type="button"
      >
        <svg aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" viewBox="0 0 24 24">
          <path d="M6 4.8A1.8 1.8 0 0 1 7.8 3h8.4A1.8 1.8 0 0 1 18 4.8V21l-6-4-6 4z" />
        </svg>
      </button>
    </article>
  );
}

function PaperCard({ paper }: { paper: PaperResult }) {
  return (
    <Link className={`explore-paper grade-card-${paper.grade || 'unknown'}`} to={`/documents/${paper.id}`}>
      <span aria-hidden="true" className="explore-paper-art">
        <span className="paper-art-year">{paper.academic_year || 'PAPER'}</span>
        <span className="paper-art-grade">{paper.grade ? `GRADE ${paper.grade}` : 'SOURCE DOCUMENT'}</span>
        <span className="paper-art-sheets"><i /><i /><i /></span>
      </span>
      <span className="explore-paper-title">{paper.title}</span>
      <span className="explore-paper-meta">
        {paper.grade ? `Grade ${paper.grade}` : 'Grade not specified'}
        {paper.subject ? ` · ${paper.subject}` : ''}
        {paper.academic_year ? ` · ${paper.academic_year}` : ''}
      </span>
      <span className="explore-paper-date">{postedDate(paper.posted_at)}</span>
    </Link>
  );
}

function ArticleCard({ article }: { article: ArticleResult }) {
  return (
    <Link className="explore-article" to={`/articles/${article.id}`}>
      <span aria-hidden="true" className="article-mark">A</span>
      <span className="explore-article-content">
        {article.subject && <span className="article-subject">{article.subject}</span>}
        <strong>{article.title}</strong>
        <span className="article-summary">{article.summary}</span>
        <span className="explore-paper-date">{postedDate(article.posted_at)}</span>
      </span>
      <span aria-hidden="true" className="article-arrow">↗</span>
    </Link>
  );
}

export default function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const query = searchParams.get('q') || '';
  const grade = searchParams.get('grade') || '';
  const subjectId = searchParams.get('subject_id') || '';
  const [draftState, setDraftState] = useState({ query, value: query });
  const draft = draftState.query === query ? draftState.value : query;
  const [activeTab, setActiveTab] = useState<ExploreTab>('all');
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectsError, setSubjectsError] = useState('');
  const [exploreState, setExploreState] = useState<{
    key: string;
    results: ExploreResults;
    error: string;
  }>({ key: '', results: { questions: [], papers: [], articles: [] }, error: '' });
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const [bookmarks, setBookmarks] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [retry, setRetry] = useState(0);
  const subjectPreferences = user?.preferred_subject_ids ?? NO_SUBJECT_PREFERENCES;
  const queryKey = useMemo(() => JSON.stringify({
    query: query.trim(),
    grade,
    subjectId,
    preferredGrade: user?.preferred_grade ?? null,
    preferredSubjects: subjectPreferences,
    retry,
  }), [query, grade, subjectId, user?.preferred_grade, subjectPreferences, retry]);

  useEffect(() => {
    const controller = new AbortController();
    api<Subject[]>('/api/v1/taxonomy/subjects', { signal: controller.signal })
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
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }
    let active = true;
    api<Bookmark[]>('/api/v1/bookmarks')
      .then((items) => {
        if (!active || !Array.isArray(items)) return;
        setBookmarks(Object.fromEntries(
          items.filter((item) => item.target_type === 'question').map((item) => [item.target_id, item.id]),
        ));
      })
      .catch((reason: unknown) => {
        if (active) setActionMessage(reason instanceof Error ? reason.message : 'Bookmark status is unavailable.');
      });
    return () => { active = false; };
  }, [user]);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (query.trim()) params.set('q', query.trim());
    if (grade) params.set('grade', grade);
    if (subjectId) params.set('subject_id', subjectId);
    if (user?.preferred_grade) params.set('preferred_grade', String(user.preferred_grade));
    subjectPreferences.forEach((id) => params.append('preferred_subject_ids', id));

    api<unknown>(`/api/v1/search/explore?${params}`, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) {
          setExploreState({ key: queryKey, results: parseExploreResults(data), error: '' });
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setExploreState({
            key: queryKey,
            results: { questions: [], papers: [], articles: [] },
            error: reason instanceof Error ? reason.message : 'Explore could not be loaded.',
          });
        }
      });
    return () => controller.abort();
  }, [queryKey, query, grade, subjectId, user?.preferred_grade, subjectPreferences]);

  useEffect(() => {
    const normalized = draft.trim();
    if (normalized.length < 2) {
      return undefined;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ q: normalized });
      if (user?.preferred_grade) params.set('preferred_grade', String(user.preferred_grade));
      subjectPreferences.forEach((id) => params.append('preferred_subject_ids', id));
      api<Suggestion[]>(`/api/v1/search/suggestions?${params}`, { signal: controller.signal })
        .then((items) => {
          if (!Array.isArray(items)) throw new Error('Search suggestions were not in the expected format.');
          if (!controller.signal.aborted) {
            setSuggestions(items);
            setSuggestionsOpen(true);
          }
        })
        .catch((reason: unknown) => {
          if (reason instanceof DOMException && reason.name === 'AbortError') return;
          if (!controller.signal.aborted) {
            setSuggestions([]);
            setSuggestionsOpen(false);
            setActionMessage(reason instanceof Error ? reason.message : 'Search suggestions could not be loaded.');
          }
        });
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [draft, user?.preferred_grade, subjectPreferences]);

  const stateIsCurrent = exploreState.key === queryKey;
  const loading = !stateIsCurrent;
  const error = stateIsCurrent ? exploreState.error : '';
  const results = stateIsCurrent ? exploreState.results : { questions: [], papers: [], articles: [] };
  const resultCount = results.questions.length + results.papers.length + results.articles.length;
  const showType = (type: Exclude<ExploreTab, 'all'>) => activeTab === 'all' || activeTab === type;

  function applyFilters(nextGrade: string, nextSubjectId: string) {
    const params: Record<string, string> = {};
    if (query.trim()) params.q = query.trim();
    if (nextGrade) params.grade = nextGrade;
    if (nextSubjectId) params.subject_id = nextSubjectId;
    setSearchParams(params);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuggestionsOpen(false);
    setActiveSuggestion(-1);
    const params: Record<string, string> = {};
    if (draft.trim()) params.q = draft.trim();
    if (grade) params.grade = grade;
    if (subjectId) params.subject_id = subjectId;
    setSearchParams(params);
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setSuggestionsOpen(false);
      setActiveSuggestion(-1);
      return;
    }
    if (!suggestionsOpen || suggestions.length === 0) {
      if (event.key === 'Enter') setSuggestionsOpen(false);
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveSuggestion((current) => (current + 1) % suggestions.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSuggestion((current) => current <= 0 ? suggestions.length - 1 : current - 1);
    } else if (event.key === 'Enter' && activeSuggestion >= 0) {
      event.preventDefault();
      navigate(suggestions[activeSuggestion].href);
      setSuggestionsOpen(false);
    }
  }

  async function toggleBookmark(result: QuestionResult) {
    if (!user) {
      navigate('/login', { state: { from: { pathname: '/search', search: searchParams.toString() } } });
      return;
    }
    setSavingId(result.id);
    setActionMessage('');
    try {
      const existing = bookmarks[result.id];
      if (existing) {
        await api(`/api/v1/bookmarks/${existing}`, { method: 'DELETE' });
        setBookmarks((current) => {
          const updated = { ...current };
          delete updated[result.id];
          return updated;
        });
        setActionMessage('Removed from bookmarks.');
      } else {
        const target = new URLSearchParams({ target_type: 'question', target_id: result.id });
        const created = await api<{ id: string }>(`/api/v1/bookmarks?${target}`, { method: 'POST' });
        setBookmarks((current) => ({ ...current, [result.id]: created.id }));
        setActionMessage('Saved to bookmarks.');
      }
    } catch (reason) {
      setActionMessage(reason instanceof Error ? reason.message : 'Bookmark could not be updated.');
    } finally {
      setSavingId('');
    }
  }

  return (
    <section className="page-content search-explore-page">
      <div className="search-intro">
        <p className="eyebrow">Search your study universe</p>
        <h1>{query ? `Explore “${query}”` : 'What are you curious about?'}</h1>
        <p className="page-description">Find questions, past papers, and useful reading from one search.</p>
      </div>

      <form className="search-composer-wrap" onSubmit={submitSearch}>
        <div className="search-composer">
          <span aria-hidden="true" className="search-leading">⌕</span>
          <label className="sr-only" htmlFor="archive-search">Search questions, papers, and articles</label>
          <input
            aria-activedescendant={activeSuggestion >= 0 ? `search-suggestion-${activeSuggestion}` : undefined}
            aria-autocomplete="list"
            aria-controls="search-suggestions"
            autoComplete="off"
            id="archive-search"
            onBlur={() => window.setTimeout(() => setSuggestionsOpen(false), 120)}
            onChange={(event) => {
              setDraftState({ query, value: event.target.value });
              setActiveSuggestion(-1);
              if (event.target.value.trim().length < 2) {
                setSuggestions([]);
                setSuggestionsOpen(false);
              }
            }}
            onFocus={() => { if (suggestions.length > 0) setSuggestionsOpen(true); }}
            onKeyDown={handleInputKeyDown}
            placeholder="Search a topic, test, year, or question…"
            role="combobox"
            value={draft}
          />
          {draft && (
            <button aria-label="Clear search" className="clear-search" onClick={() => {
              setDraftState({ query, value: '' });
              setSearchParams({});
            }} type="button">×</button>
          )}
          <button aria-label="Search archive" className="search-submit-button" disabled={!draft.trim()} type="submit">
            <span>Search</span><span aria-hidden="true">↗</span>
          </button>
        </div>
        {suggestionsOpen && suggestions.length > 0 && (
          <div className="search-suggestions" id="search-suggestions" role="listbox" aria-label="Search suggestions">
            {suggestions.map((suggestion, index) => (
              <Link
                aria-selected={index === activeSuggestion}
                className={`search-suggestion ${index === activeSuggestion ? 'is-active' : ''}`}
                id={`search-suggestion-${index}`}
                key={`${suggestion.type}-${suggestion.id}`}
                onMouseEnter={() => setActiveSuggestion(index)}
                role="option"
                to={suggestion.href}
              >
                <span aria-hidden="true" className={`suggestion-kind suggestion-${suggestion.type}`}>
                  {suggestion.type === 'question' ? '?' : suggestion.type === 'paper' ? 'P' : 'A'}
                </span>
                <span className="suggestion-copy"><strong>{suggestion.label}</strong><small>{suggestion.detail}</small></span>
                <span aria-hidden="true" className="suggestion-arrow">↗</span>
              </Link>
            ))}
          </div>
        )}
      </form>

      <div className="explore-controls">
        <div aria-label="Explore content type" className="explore-tabs" role="tablist">
          {TAB_OPTIONS.map((tab) => (
            <button
              aria-selected={activeTab === tab.id}
              className={`explore-tab ${activeTab === tab.id ? 'is-active' : ''}`}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              role="tab"
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="explore-filters">
          <label>
            <span className="sr-only">Filter by grade</span>
            <select onChange={(event) => applyFilters(event.target.value, subjectId)} value={grade}>
              <option value="">All grades</option>
              {[9, 10, 11, 12].map((value) => <option key={value} value={value}>Grade {value}</option>)}
            </select>
          </label>
          <label>
            <span className="sr-only">Filter by subject</span>
            <select
              onChange={(event) => applyFilters(grade, event.target.value)}
              value={subjectId}
            >
              <option value="">All subjects</option>
              {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
            </select>
          </label>
        </div>
      </div>
      {subjectsError && <p className="search-catalog-note" role="status">{subjectsError} Subject filters are temporarily unavailable.</p>}

      {actionMessage && <p aria-live="polite" className="inline-feedback">{actionMessage}</p>}
      {loading && (
        <div aria-label="Searching the archive" className="loading-list" role="status">
          <span /><span /><span />
        </div>
      )}
      {!loading && error && (
        <div className="state-card state-error" role="alert">
          <strong>Explore could not be loaded</strong>
          <p>{error}</p>
          <button className="button button-secondary" onClick={() => setRetry((current) => current + 1)} type="button">Try again</button>
        </div>
      )}
      {!loading && !error && resultCount === 0 && (
        <div className="feed-empty explore-empty">
          <strong>{query ? 'No close matches yet.' : 'Your archive is getting started.'}</strong>
          <p>{query
            ? 'Try another phrase, use fewer words, or broaden your grade and subject filters.'
            : 'Newly reviewed questions, source papers, and published articles will appear here.'}</p>
          {query && <button className="button button-secondary" onClick={() => applyFilters('', '')} type="button">Clear filters</button>}
        </div>
      )}

      {!loading && !error && resultCount > 0 && (
        <div className="explore-content">
          {showType('questions') && results.questions.length > 0 && (
            <section aria-labelledby="questions-heading" className="explore-section">
              <div className="explore-section-heading">
                <div><p className="eyebrow">{query ? 'Best keyword matches' : 'Start practicing'}</p><h2 id="questions-heading">Questions</h2></div>
                <span>{results.questions.length}</span>
              </div>
              <div aria-label={`${results.questions.length} question results`} className="result-list">
                {results.questions.map((result, index) => (
                  <SearchResultQuestion
                    bookmarkId={user ? bookmarks[result.id] : undefined}
                    index={index}
                    key={result.id}
                    onBookmark={() => void toggleBookmark(result)}
                    result={result}
                    saving={savingId === result.id}
                  />
                ))}
              </div>
            </section>
          )}
          {showType('papers') && results.papers.length > 0 && (
            <section aria-labelledby="papers-heading" className="explore-section">
              <div className="explore-section-heading">
                <div><p className="eyebrow">{query ? 'Source documents' : 'From the archive'}</p><h2 id="papers-heading">Past papers & tests</h2></div>
                <span>{results.papers.length}</span>
              </div>
              <div className="explore-paper-grid">{results.papers.map((paper) => <PaperCard key={paper.id} paper={paper} />)}</div>
            </section>
          )}
          {showType('articles') && results.articles.length > 0 && (
            <section aria-labelledby="articles-heading" className="explore-section">
              <div className="explore-section-heading">
                <div><p className="eyebrow">Read, review, understand</p><h2 id="articles-heading">Articles & study guides</h2></div>
                <span>{results.articles.length}</span>
              </div>
              <div className="explore-article-grid">{results.articles.map((article) => <ArticleCard article={article} key={article.id} />)}</div>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
