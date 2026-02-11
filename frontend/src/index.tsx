import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles/index.css';
import './i18n';
import App from './App';
import ErrorBoundary from './components/ui/ErrorBoundary';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nextProvider } from 'react-i18next';
import i18n from './i18n';
import { QUERY_CACHE_CONFIG } from './config/constants';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: QUERY_CACHE_CONFIG.STALE_TIME,
      gcTime: QUERY_CACHE_CONFIG.GC_TIME,
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        return failureCount < QUERY_CACHE_CONFIG.MAX_RETRY_ATTEMPTS;
      },
      refetchOnWindowFocus: true, // Default refetch on window focus
    },
    mutations: {
      retry: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root')!);
root.render(
  <React.StrictMode>
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </QueryClientProvider>
    </I18nextProvider>
  </React.StrictMode>
);
