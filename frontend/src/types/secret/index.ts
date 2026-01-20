// Типы для секретов

export interface Secret {
  id: number;
  name: string;
  description?: string;
  secret_type: 'password' | 'ssh_key' | 'kubeconfig';
  encrypted_data: string;
  secret_metadata?: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
}

export interface SecretCreateRequest {
  name: string;
  description?: string;
  secret_type: 'password' | 'ssh_key' | 'kubeconfig';
  data: string; // Нешифрованные данные
}

export interface SecretUpdateRequest {
  description?: string;
  data?: string;
  is_active?: boolean;
}

export interface EncryptionKey {
  id: number;
  key_name: string;
  encryption_key: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
