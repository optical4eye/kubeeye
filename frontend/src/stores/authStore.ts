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

interface LdapStatus {
  enabled: boolean;
  available: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  ldapStatus: LdapStatus | null;
  login: (username: string, password: string, authType?: 'local' | 'ldap') => Promise<void>;
  logout: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  checkAuth: () => boolean;
  fetchLdapStatus: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      ldapStatus: null,

      login: async (username: string, password: string, authType?: 'local' | 'ldap') => {
        set({ isLoading: true });
        try {
          const requestData: { username: string; password: string; auth_type?: string } = {
            username,
            password,
          };

          if (authType) {
            requestData.auth_type = authType;
          }

          const response = await api.post('/api/auth/login', requestData);

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

      fetchLdapStatus: async () => {
        try {
          const response = await api.get('/api/auth/ldap-status');
          set({ ldapStatus: response.data });
        } catch (error) {
          console.error('Failed to fetch LDAP status:', error);
          set({ ldapStatus: { enabled: false, available: false } });
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
