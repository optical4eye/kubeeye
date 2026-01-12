/**
 * Secret types for the frontend
 */

export enum SecretType {
  PASSWORD = 'password',
  SSH_KEY = 'ssh_key',
  KUBECONFIG = 'kubeconfig',
}

export interface Secret {
  id: number;
  name: string;
  description?: string;
  secret_type: SecretType;
  metadata?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

export interface SecretCreate {
  name: string;
  secret_type: SecretType;
  data: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface SecretUpdate {
  name?: string;
  data?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  is_active?: boolean;
}

export interface SecretReveal {
  id: number;
  name: string;
  secret_type: SecretType;
  data: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface SecretTestResult {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export interface SecretListResponse {
  secrets: Secret[];
  total: number;
  filtered: number;
}

export interface SecretFilter {
  secret_type?: SecretType;
  is_active?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}
