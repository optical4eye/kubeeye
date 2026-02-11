import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  theme: 'light' | 'dark';
  language: 'ru' | 'en';
  setTheme: (theme: 'light' | 'dark') => void;
  setLanguage: (language: 'ru' | 'en') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    set => ({
      theme: 'dark',
      language: 'en',
      setTheme: theme => set({ theme }),
      setLanguage: language => set({ language }),
    }),
    {
      name: 'ui-store',
      partialize: state => ({
        theme: state.theme,
        language: state.language,
      }),
    }
  )
);
