import { useState, useEffect, useCallback } from 'react';
import { getSettings, saveSettings } from '../utils/storage';

type ThemeMode = 'auto' | 'light' | 'dark';

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => getSettings().darkMode);

  const applyTheme = useCallback((m: ThemeMode) => {
    const isDark =
      m === 'dark' ||
      (m === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);

    document.documentElement.classList.toggle('dark', isDark);
  }, []);

  useEffect(() => {
    applyTheme(mode);

    if (mode === 'auto') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = () => applyTheme('auto');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
  }, [mode, applyTheme]);

  const cycleTheme = useCallback(() => {
    const next: ThemeMode = mode === 'auto' ? 'light' : mode === 'light' ? 'dark' : 'auto';
    setMode(next);
    const settings = getSettings();
    saveSettings({ ...settings, darkMode: next });
  }, [mode]);

  return { mode, cycleTheme };
}
