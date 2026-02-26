import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';
import { tokenStorage } from '../utils/tokenStorage';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

interface OAuthStatus {
  enabled: boolean;
  configured: boolean;
  connected: boolean;
  message: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  oauthStatus: OAuthStatus | null;

  // Local login (for admin/emergency access)
  login: (username: string, password: string) => Promise<void>;

  // OAuth login
  initiateOAuthLogin: () => Promise<void>;
  handleOAuthCallback: (code: string, state: string) => Promise<void>;

  logout: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  checkAuth: () => boolean;
  fetchOAuthStatus: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      oauthStatus: null,

      // Local login (admin only)
      login: async (username: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await api.post('/api/auth/login', { username, password });

          const { access_token, user } = response.data;

          // Store access token
          tokenStorage.setAccessToken(access_token);

          // Update state
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      // OAuth: Initiate login (redirect to Dex)
      initiateOAuthLogin: async () => {
        set({ isLoading: true });
        try {
          const response = await api.get('/api/oauth/auth-url');
          const { authorization_url } = response.data;

          // Redirect to Dex for authentication
          window.location.href = authorization_url;
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      // OAuth: Handle callback from Dex
      handleOAuthCallback: async (code: string, state: string) => {
        set({ isLoading: true });
        try {
          const response = await api.post('/api/oauth/callback', null, {
            params: { code, state },
          });

          const { access_token, user } = response.data;

          // Store access token
          tokenStorage.setAccessToken(access_token);

          // Update state
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        try {
          await api.post('/api/auth/logout');
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          // Clear token and state
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
          });
        }
      },

      getCurrentUser: async () => {
        try {
          const response = await api.get('/api/auth/me');
          set({
            user: response.data,
            isAuthenticated: true,
          });
        } catch (error) {
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
          });
          throw error;
        }
      },

      checkAuth: () => {
        return tokenStorage.hasToken() && get().isAuthenticated;
      },

      fetchOAuthStatus: async () => {
        try {
          const response = await api.get('/api/oauth/status');
          set({ oauthStatus: response.data });
        } catch (error) {
          console.error('Failed to fetch OAuth status:', error);
          set({
            oauthStatus: {
              enabled: false,
              configured: false,
              connected: false,
              message: 'OAuth unavailable',
            },
          });
        }
      },
    }),
    {
      name: 'auth-store',
      partialize: state => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
