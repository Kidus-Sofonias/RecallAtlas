import { createContext, useCallback, useContext, useRef, useState } from 'react';

type AccountPromptContextValue = {
  views: number;
  recordView: () => void;
  reset: () => void;
  open: boolean;
  setOpen: (open: boolean) => void;
};

const STORAGE_KEY = 'ra_question_views';
const PROMPT_THRESHOLD = 3;

export const AccountPromptContext = createContext<AccountPromptContextValue | null>(null);

export function AccountPromptProvider({ children }: { children: React.ReactNode }) {
  const [views, setViews] = useState(() => {
    try {
      return Number(localStorage.getItem(STORAGE_KEY) || '0');
    } catch {
      return 0;
    }
  });
  const viewsRef = useRef(views);
  const [open, setOpen] = useState(false);

  const recordView = useCallback(() => {
    const next = viewsRef.current + 1;
    viewsRef.current = next;
    setViews(next);
    try {
      localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      // Storage unavailable; keep counting in memory only.
    }
    if (next >= PROMPT_THRESHOLD && next % PROMPT_THRESHOLD === 0) {
      setOpen(true);
    }
  }, []);

  const reset = useCallback(() => {
    viewsRef.current = 0;
    setViews(0);
    setOpen(false);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // no-op
    }
  }, []);

  return (
    <AccountPromptContext.Provider value={{ views, recordView, reset, open, setOpen }}>
      {children}
    </AccountPromptContext.Provider>
  );
}

export function useAccountPrompt() {
  const context = useContext(AccountPromptContext);
  if (!context) {
    throw new Error('useAccountPrompt must be used within AccountPromptProvider.');
  }
  return context;
}
