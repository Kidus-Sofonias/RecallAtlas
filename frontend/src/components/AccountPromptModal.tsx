import { useNavigate } from 'react-router-dom';
import { useAccountPrompt } from '../accountPromptContext';

export default function AccountPromptModal() {
  const { open, setOpen } = useAccountPrompt();
  const navigate = useNavigate();

  if (!open) return null;

  return (
    <div className="prompt-overlay" role="dialog" aria-modal="true" aria-label="Create an account or sign in">
      <section className="prompt-card">
        <h2>Keep exploring Recall Atlas</h2>
        <p>
          You&rsquo;ve viewed a few question sets. Create a free account to save bookmarks, build
          collections, and keep your progress across sessions.
        </p>
        <div className="prompt-actions">
          <button
            className="button button-primary"
            onClick={() => {
              setOpen(false);
              navigate('/register');
            }}
            type="button"
          >
            Create an account
          </button>
          <button
            className="button button-secondary"
            onClick={() => {
              setOpen(false);
              navigate('/login');
            }}
            type="button"
          >
            Sign in
          </button>
          <button
            className="button button-ghost"
            onClick={() => setOpen(false)}
            type="button"
          >
            Continue browsing
          </button>
        </div>
      </section>
    </div>
  );
}
