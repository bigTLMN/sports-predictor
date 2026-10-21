'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Theme = 'light' | 'dark';
export const THEME_STORAGE_KEY = 'edge-analytics-theme';
export const FONT_STORAGE_KEY = 'edge-analytics-font';
export const FONT_MIN = 12;
export const FONT_MAX = 18;
export const FONT_DEFAULT = 18;

type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  fontSize: number;
  setFontSize: (size: number) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

function clampFont(size: number) {
  if (!Number.isFinite(size)) return FONT_DEFAULT;
  return Math.min(FONT_MAX, Math.max(FONT_MIN, Math.round(size)));
}

function applyFontSize(size: number) {
  document.documentElement.style.fontSize = `${size}px`;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('dark');
  const [fontSize, setFontSizeState] = useState(FONT_DEFAULT);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(THEME_STORAGE_KEY);
      const next: Theme = saved === 'light' ? 'light' : 'dark';
      setThemeState(next);
      applyTheme(next);
    } catch {
      applyTheme('dark');
    }
    try {
      const savedSize = Number(localStorage.getItem(FONT_STORAGE_KEY));
      const nextSize = clampFont(savedSize || FONT_DEFAULT);
      setFontSizeState(nextSize);
      applyFontSize(nextSize);
    } catch {
      applyFontSize(FONT_DEFAULT);
    }
  }, []);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    applyTheme(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  const setFontSize = useCallback((size: number) => {
    const next = clampFont(size);
    setFontSizeState(next);
    applyFontSize(next);
    try {
      localStorage.setItem(FONT_STORAGE_KEY, String(next));
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, fontSize, setFontSize }),
    [theme, setTheme, fontSize, setFontSize]
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
