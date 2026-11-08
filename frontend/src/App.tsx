import { AuthProvider } from './authProvider';
import { useAuth } from './authContext';
import { AccountPromptProvider, useAccountPrompt } from './accountPromptContext';
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import type { ReactNode } from 'react';
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import './App.css';
import { api } from './api';
import Admin from './pages/Admin';
import Bookmarks from './pages/Bookmarks';
import Collections from './pages/Collections';
import Document from './pages/Document';
import Notifications from './pages/Notifications';
import Question from './pages/Question';
import Search from './pages/Search';
import Auth, { PasswordReset } from './pages/Auth';
import Account from './pages/Account';
import Onboarding from './pages/Onboarding';
import Upload from './pages/Upload';
import Terms from './pages/Terms';
import Article from './pages/Article';
import AccountPromptModal from './components/AccountPromptModal';

type IconName =
  | 'home'
  | 'search'
  | 'bookmark'
  | 'collection'
  | 'bell'
  | 'arrow'
  | 'account'
  | 'upload'
  | 'add';

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    home: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-6h6v6" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 5 5" /></>,
    bookmark: <path d="M6 4.8A1.8 1.8 0 0 1 7.8 3h8.4A1.8 1.8 0 0 1 18 4.8V21l-6-4-6 4z" />,
    collection: <><rect x="3" y="4" width="15" height="16" rx="2" /><path d="M7 8h7M7 12h7M7 16h4M20 8v12" /></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
    arrow: <><path d="M7 17 17 7M7 7h10v10" /></>,
    account: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
    upload: <><path d="M3 16v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6M21 12l-5-5-5 5" /></>,
    add: <><path d="M12 5v14M5 12h14" /></>,
  };

  return (
    <svg
      aria-hidden="true"
      className="icon"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
    >
      {paths[name]}
    </svg>
  );
}

const navigation: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: '/', label: 'Home', icon: 'home', end: true },
  { to: '/search', label: 'Search', icon: 'search' },
];

const libraryNavigation: { to: string; label: string; icon: IconName }[] = [
  { to: '/collections', label: 'Collections', icon: 'collection' },
  { to: '/bookmarks', label: 'Bookmarks', icon: 'bookmark' },
  { to: '/upload', label: 'Upload', icon: 'upload' },
];

const accountNavigation: { to: string; label: string; icon: IconName }[] = [
  { to: '/notifications', label: 'Notifications', icon: 'bell' },
];

function NavigationLink({
  to,
  label,
  icon,
  end,
}: {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}) {
  return (
    <NavLink className={`nav-link ${to === '/upload' ? 'nav-upload' : ''}`} end={end} to={to}>
      <Icon name={icon} />
      <span>{label}</span>
    </NavLink>
  );
}

function Brand() {
  return (
    <Link aria-label="Recall Atlas home" className="brand" to="/">
      <span aria-hidden="true" className="brand-mark">
        <span />
        <span />
        <span />
        <span />
      </span>
      <span className="brand-copy">
        <strong>Recall Atlas</strong>
        <small>Find it. Understand it. Remember it.</small>
      </span>
    </Link>
  );
}

function AccountActions() {
  const { user, loading } = useAuth();
  if (loading) return <div aria-label="Checking account" className="header-account-actions" />;
  if (user) {
    const name = user.display_name || 'Your profile';
    return (
      <div className="header-account-actions">
        <Link aria-label={name} className="profile-action" to="/profile">
          <span aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>
          <span className="profile-action-label">Profile</span>
        </Link>
      </div>
    );
  }
  return (
    <div className="header-account-actions">
      <Link className="header-login" to="/login">Log in</Link>
      <Link className="button button-primary header-signup" to="/register">Sign up</Link>
    </div>
  );
}

type DiscoveryItem = {
  id: string;
  document_id: string;
  page: number | null;
  snippet: string;
  title: string;
  grade: number | null;
  academic_year: number | null;
  posted_by: string;
  posted_at: string | null;
};

type DiscoveryFeed = {
  recent: DiscoveryItem[];
  for_you: DiscoveryItem[];
  grade: number | null;
};

function postedDate(value: string | null): string {
  if (!value) return 'Date not listed';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Date not listed';

  const days = Math.floor((Date.now() - date.getTime()) / 86_400_000);
  if (days < 1) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
}

function QuestionCard({ item }: { item: DiscoveryItem }) {
  return (
    <article className={`featured-card grade-card-${item.grade || 'unknown'}`}>
      <Link aria-label={`Open ${item.title}`} className="featured-art" to={`/questions/${item.id}`}>
        <span className="art-orbit art-orbit-one" />
        <span className="art-orbit art-orbit-two" />
        <span className="art-edition">{item.academic_year || 'ARCHIVE'}</span>
        <span className="art-grade">{item.grade ? `GRADE ${item.grade}` : 'PAST PAPER'}</span>
        <span aria-hidden="true" className="art-question-mark">?</span>
        <span className="art-paper-lines"><i /><i /><i /></span>
        <span className="art-open">Open question <span aria-hidden="true">↗</span></span>
      </Link>
      <div className="featured-card-body">
        <div className="featured-tags">
          {item.grade && <span>Grade {item.grade}</span>}
          {item.academic_year && <span>{item.academic_year}</span>}
        </div>
        <Link className="featured-title" to={`/questions/${item.id}`}>{item.title}</Link>
        <p className="featured-snippet">{item.snippet || 'Open this question to view its extracted text and source.'}</p>
        <div className="featured-meta">
          <span className="contributor-avatar" aria-hidden="true">{item.posted_by.slice(0, 1).toUpperCase()}</span>
          <span className="featured-author">{item.posted_by}</span>
          <span className="meta-separator">·</span>
          <time dateTime={item.posted_at || undefined}>{postedDate(item.posted_at)}</time>
        </div>
        <Link className="featured-source" to={`/documents/${item.document_id}`}>View source paper <span aria-hidden="true">→</span></Link>
      </div>
    </article>
  );
}

function Home() {
  const { user } = useAuth();
  const [feed, setFeed] = useState<DiscoveryFeed | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const grade = user?.preferred_grade ?? null;

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (grade) params.set('grade', String(grade));
    api<DiscoveryFeed>(`/api/v1/discovery${params.size ? `?${params}` : ''}`, { signal: controller.signal })
      .then((result) => {
        if (!Array.isArray(result.recent) || !Array.isArray(result.for_you)) {
          throw new Error('The discovery feed was not in the expected format.');
        }
        if (!controller.signal.aborted) {
          setFeed(result);
          setError('');
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'The discovery feed could not be loaded.');
        }
      });
    return () => controller.abort();
  }, [grade, retry]);

  return (
    <div className="home-page">
      <section className="home-hero">
        <div className="hero-orb hero-orb-left" />
        <div className="hero-orb hero-orb-right" />
        <div className="eyebrow"><span className="eyebrow-dot" /> A better way to study</div>
        <h1>Find your next<br /><em>“aha”</em> moment.</h1>
        <p className="hero-copy">Past papers, real questions, and a little more clarity — all in one place.</p>
        <SearchForm />
        <div className="hero-footnote">
          <span><i /> Search by topic or exam</span>
          <span><i /> Follow every question to its source</span>
        </div>
      </section>

      <section aria-labelledby="browse-grades" className="grade-browser">
        <div className="section-heading">
          <div><p className="eyebrow">Start where you are</p><h2 id="browse-grades">Browse by grade</h2></div>
          <Link className="section-link" to="/search">Explore all <span aria-hidden="true">↗</span></Link>
        </div>
        <div className="grade-pills">
          {[9, 10, 11, 12].map((value) => (
            <Link className={`grade-pill grade-pill-${value}`} key={value} to={`/search?grade=${value}`}>
              <span className="grade-pill-number">{value}</span>
              <span>Grade {value}<small>Past papers & questions</small></span>
              <span aria-hidden="true" className="grade-pill-arrow">↗</span>
            </Link>
          ))}
        </div>
      </section>

      {grade && (
        <section aria-labelledby="recommended-heading" className="feed-section">
          <div className="section-heading">
            <div><p className="eyebrow">Picked for your grade</p><h2 id="recommended-heading">More for Grade {grade}</h2></div>
          </div>
          {feed && feed.for_you.length > 0 ? (
            <div className="featured-grid">{feed.for_you.map((item) => <QuestionCard item={item} key={item.id} />)}</div>
          ) : feed ? (
            <div className="feed-empty"><strong>Your Grade {grade} shelf is waiting.</strong><p>Newly reviewed papers for your grade will show up here.</p></div>
          ) : null}
        </section>
      )}

      <section aria-labelledby="recent-heading" className="feed-section recent-section">
        <div className="section-heading">
          <div><p className="eyebrow">Fresh from the community</p><h2 id="recent-heading">Recently added</h2></div>
          <Link className="section-link" to="/search">Search the archive <span aria-hidden="true">↗</span></Link>
        </div>
        {error ? (
          <div className="state-card state-error" role="alert">
            <strong>The archive could not be loaded</strong><p>{error}</p>
            <button className="button button-secondary" onClick={() => setRetry((value) => value + 1)} type="button">Try again</button>
          </div>
        ) : !feed ? (
          <div aria-label="Loading questions" className="featured-grid featured-grid-loading" role="status"><span /><span /><span /></div>
        ) : feed.recent.length > 0 ? (
          <div className="featured-grid">{feed.recent.map((item) => <QuestionCard item={item} key={item.id} />)}</div>
        ) : grade && feed.for_you.length > 0 ? (
          <div className="feed-empty">
            <strong>You’re all caught up on new papers.</strong>
            <p>Your latest Grade {grade} questions are in the section above.</p>
            <Link className="section-link" to="/search">Explore the full archive <span aria-hidden="true">↗</span></Link>
          </div>
        ) : (
          <div className="feed-empty">
            <strong>The first paper is waiting to be shared.</strong>
            <p>Reviewed questions from the community will appear here. Have a past paper? Add it to the archive.</p>
            <Link className="button button-primary" to={user ? '/upload' : '/register'}>{user ? 'Upload a paper' : 'Join the community'} <span aria-hidden="true">↗</span></Link>
          </div>
        )}
      </section>
    </div>
  );
}

function SearchForm() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    navigate(value ? `/search?q=${encodeURIComponent(value)}` : '/search');
  }

  return (
    <form className="hero-search" onSubmit={submit}>
      <Icon name="search" />
      <input
        aria-label="Search questions, exams, topics, or resources"
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search questions, exams, topics, or resources…"
        value={query}
      />
      <button className="button button-primary" disabled={!query.trim()} type="submit">
        Search <span aria-hidden="true">↗</span>
      </button>
    </form>
  );
}

function UnavailablePage({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="page-content">
      <div className="page-heading">
        <p className="eyebrow">Recall Atlas</p>
        <h1>{title}</h1>
      </div>
      <div className="notice-card">
        <span aria-hidden="true" className="notice-mark">i</span>
        <div>
          <h2>This feature is not available yet</h2>
          <p>{detail}</p>
          <Link className="text-link" to="/search">Search the archive <span aria-hidden="true">→</span></Link>
        </div>
      </div>
    </section>
  );
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p className="auth-loading" role="status">Checking your session…</p>;
  if (!user) return <Navigate replace state={{ from: location }} to="/login" />;
  if (user.role !== 'admin' && !user.onboarding_completed && location.pathname !== '/onboarding') {
    return <Navigate replace to="/onboarding" />;
  }
  return children;
}

function AppLayout() {
  const { user, error: authError } = useAuth();
  const { reset } = useAccountPrompt();
  const location = useLocation();

  useEffect(() => {
    if (user && (user.role === 'admin' || user.onboarding_completed)) {
      reset();
    }
  }, [user, reset]);

  const showAccountPrompt =
    location.pathname !== '/login' &&
    location.pathname !== '/register' &&
    location.pathname !== '/reset-password';
  return (
    <div className="app-shell">
      <aside aria-label="Main navigation" className="sidebar">
        <Brand />
        <div className="sidebar-rule" />
        <div className="nav-group">
          <p className="nav-label">Discover</p>
          {navigation.map((item) => <NavigationLink key={item.to} {...item} />)}
        </div>
        <div className="nav-group">
          <p className="nav-label">Your library</p>
          {libraryNavigation.map((item) => <NavigationLink key={item.to} {...item} />)}
        </div>
        <div className="nav-group">
          <p className="nav-label">Account</p>
          {accountNavigation.map((item) => <NavigationLink key={item.to} {...item} />)}
          <NavigationLink
            icon="account"
            label={user ? 'Account' : 'Sign in'}
            to={user ? '/account' : '/login'}
          />
        </div>
        <div className="sidebar-bottom">
          <div aria-hidden="true" className="sidebar-coordinate">
            <span>RA</span><i /><i /><i />
          </div>
          <p>Knowledge, mapped<br />to its source.</p>
          <small>RECALL ATLAS · ARCHIVE</small>
        </div>
      </aside>

      <div className="main-column">
        <header className="mobile-header"><Brand /><AccountActions /></header>
        <header className="desktop-header"><span>Questions worth coming back to.</span><AccountActions /></header>
        <main className="main-content">
          {authError && <div className="inline-error" role="alert">{authError}</div>}
          <Routes>
            <Route element={<Home />} path="/" />
            <Route element={<Search />} path="/search" />
            <Route element={<Question />} path="/questions/:id" />
            <Route element={<Document />} path="/documents/:id" />
            <Route element={<Article />} path="/articles/:id" />
            <Route element={<RequireAuth><Upload /></RequireAuth>} path="/upload" />
            <Route element={<RequireAuth><Collections /></RequireAuth>} path="/collections" />
            <Route element={<RequireAuth><Bookmarks /></RequireAuth>} path="/bookmarks" />
            <Route element={<RequireAuth><Notifications /></RequireAuth>} path="/notifications" />
            <Route element={<RequireAuth><Account /></RequireAuth>} path="/account" />
            <Route element={<RequireAuth><Account /></RequireAuth>} path="/profile" />
            <Route element={<Auth mode="login" />} path="/login" />
            <Route element={<Auth mode="register" />} path="/register" />
            <Route element={<PasswordReset />} path="/reset-password" />
            <Route element={<Auth mode="verify" />} path="/verify-email" />
            <Route element={<RequireAuth><Onboarding /></RequireAuth>} path="/onboarding" />
            <Route element={<Terms />} path="/terms" />
            <Route element={<RequireAuth><Admin /></RequireAuth>} path="/admin" />
            <Route element={<UnavailablePage detail="This destination has no implemented API or page yet." title="Page not found" />} path="*" />
          </Routes>
        </main>
      </div>

      {showAccountPrompt && <AccountPromptModal />}

      <nav aria-label="Mobile navigation" className="mobile-nav">
        {[
          ...navigation,
          { to: '/upload', label: 'Upload', icon: 'add' as const },
          { to: user ? '/profile' : '/login', label: 'Profile', icon: 'account' as const },
        ].map((item) => (
          <NavigationLink key={item.to} {...item} />
        ))}
      </nav>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AccountPromptProvider>
          <AppLayout />
        </AccountPromptProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
