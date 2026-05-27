import { useState, useEffect, useCallback } from 'react';

export interface UseThemeReturn {
  theme: string;
  toggleTheme: () => void;
  isDark: boolean;
}

export default function useTheme(): UseThemeReturn {
  const [theme, setTheme] = useState<string>(() => {
    return localStorage.getItem('richman-theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('richman-theme', theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, toggleTheme, isDark: theme === 'dark' };
}
