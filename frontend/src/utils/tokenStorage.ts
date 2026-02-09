/**
 * Token storage utilities
 */

const ACCESS_TOKEN_KEY = 'access_token';

export const tokenStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  setAccessToken(token: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  },

  clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  },

  hasToken(): boolean {
    return !!this.getAccessToken();
  }
};
