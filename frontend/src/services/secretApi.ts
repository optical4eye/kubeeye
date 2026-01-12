/**
 * API service for secret management
 */

import axios from 'axios';
import {
  Secret,
  SecretCreate,
  SecretUpdate,
  SecretReveal,
  SecretTestResult,
  SecretListResponse,
  SecretFilter,
  SecretType,
} from '../types/secret';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export const secretApi = {
  /**
   * List secrets with optional filters
   */
  listSecrets: async (filters?: SecretFilter): Promise<SecretListResponse> => {
    const params = new URLSearchParams();

    if (filters?.secret_type) {
      params.append('secret_type', filters.secret_type);
    }
    if (filters?.is_active !== undefined) {
      params.append('is_active', String(filters.is_active));
    }
    if (filters?.search) {
      params.append('search', filters.search);
    }
    if (filters?.limit) {
      params.append('limit', String(filters.limit));
    }
    if (filters?.offset) {
      params.append('offset', String(filters.offset));
    }

    const response = await axios.get<SecretListResponse>(
      `${API_BASE_URL}/secrets?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get a single secret by ID
   */
  getSecret: async (id: number): Promise<Secret> => {
    const response = await axios.get<Secret>(`${API_BASE_URL}/secrets/${id}`);
    return response.data;
  },

  /**
   * Create a new secret
   */
  createSecret: async (secret: SecretCreate): Promise<Secret> => {
    const response = await axios.post<Secret>(`${API_BASE_URL}/secrets`, secret);
    return response.data;
  },

  /**
   * Update an existing secret
   */
  updateSecret: async (id: number, secret: SecretUpdate): Promise<Secret> => {
    const response = await axios.put<Secret>(`${API_BASE_URL}/secrets/${id}`, secret);
    return response.data;
  },

  /**
   * Delete a secret
   */
  deleteSecret: async (id: number, hardDelete: boolean = false): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/secrets/${id}`, {
      params: { hard_delete: hardDelete },
    });
  },

  /**
   * Reveal (decrypt) secret data
   */
  revealSecret: async (id: number): Promise<SecretReveal> => {
    const response = await axios.post<SecretReveal>(`${API_BASE_URL}/secrets/${id}/reveal`);
    return response.data;
  },

  /**
   * Test if a secret is valid
   */
  testSecret: async (id: number): Promise<SecretTestResult> => {
    const response = await axios.post<SecretTestResult>(`${API_BASE_URL}/secrets/${id}/test`);
    return response.data;
  },

  /**
   * Get secrets by type
   */
  getSecretsByType: async (type: SecretType): Promise<Secret[]> => {
    const response = await secretApi.listSecrets({ secret_type: type, is_active: true });
    return response.secrets;
  },
};
