import { useState, useCallback } from 'react';
import type { MessageInstance } from 'antd/es/message/interface';
import { useTranslation } from 'react-i18next';
import { getUsers, createUser, updateUser, deleteUser } from '../services/api';

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  auth_type: string; // 'local' or 'ldap'
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface UserCreateData {
  username: string;
  email: string;
  password: string;
  role: string;
  is_active: boolean;
}

export interface UserUpdateData {
  email?: string;
  role?: string;
  is_active?: boolean;
}

interface UseUsersOptions {
  /** Message API instance from App.useApp() */
  messageApi?: MessageInstance;
}

export const useUsers = (options?: UseUsersOptions) => {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchUsers = useCallback(async (skip = 0, limit = 100) => {
    setLoading(true);
    try {
      const response = await getUsers(skip, limit);
      setUsers(response.data);
      setTotal(response.data.length);
    } catch (error) {
      options?.messageApi?.error(t('userManagement.title') + ': ' + t('errors.loadClusters'));
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const createUserMutation = useCallback(
    async (userData: UserCreateData) => {
      setLoading(true);
      try {
        const response = await createUser(userData);
        options?.messageApi?.success(t('userManagement.messages.createSuccess'));
        await fetchUsers();
        return response.data;
      } catch (error: any) {
        options?.messageApi?.error(
          error.response?.data?.detail || t('userManagement.messages.createError')
        );
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [fetchUsers]
  );

  const updateUserMutation = useCallback(
    async (userId: number, userData: UserUpdateData) => {
      setLoading(true);
      try {
        const response = await updateUser(userId, userData);
        options?.messageApi?.success(t('userManagement.messages.updateSuccess'));
        await fetchUsers();
        return response.data;
      } catch (error: any) {
        options?.messageApi?.error(
          error.response?.data?.detail || t('userManagement.messages.updateError')
        );
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [fetchUsers]
  );

  const deleteUserMutation = useCallback(
    async (userId: number) => {
      setLoading(true);
      try {
        await deleteUser(userId);
        options?.messageApi?.success(t('userManagement.messages.deleteSuccess'));
        await fetchUsers();
      } catch (error: any) {
        options?.messageApi?.error(
          error.response?.data?.detail || t('userManagement.messages.deleteError')
        );
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [fetchUsers]
  );

  return {
    users,
    loading,
    total,
    fetchUsers,
    createUser: createUserMutation,
    updateUser: updateUserMutation,
    deleteUser: deleteUserMutation,
  };
};
