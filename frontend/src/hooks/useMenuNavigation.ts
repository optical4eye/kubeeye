import { useState, useEffect, useCallback } from 'react';
import { MenuItem } from '../types/menu';
import { MenuNavigationState, MenuNavigationActions } from '../types/menu';

const SIDEBAR_COLLAPSED_KEY = 'sidebarCollapsed';
const MENU_OPEN_KEYS_KEY = 'menuOpenKeys';

/**
 * Custom hook for managing menu navigation state and logic
 * Provides centralized menu state management with localStorage persistence
 */
export const useMenuNavigation = (
  menuItems: MenuItem[]
): MenuNavigationState & MenuNavigationActions => {
  // Initialize collapsed state from localStorage
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
      return saved ? JSON.parse(saved) : false;
    } catch {
      return false;
    }
  });

  // Initialize open keys from localStorage
  const [openKeys, setOpenKeys] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(MENU_OPEN_KEYS_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Persist collapsed state to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, JSON.stringify(collapsed));
    } catch {
      // Ignore localStorage errors
    }
  }, [collapsed]);

  // Persist open keys to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(MENU_OPEN_KEYS_KEY, JSON.stringify(openKeys));
    } catch {
      // Ignore localStorage errors
    }
  }, [openKeys]);

  // Toggle collapsed state
  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => !prev);
  }, []);

  /**
   * Check if a menu key is a leaf node (not a group)
   * @param key - Menu key to check
   * @returns true if the key is a leaf node
   */
  const isLeafNode = useCallback(
    (key: string): boolean => {
      return menuItems.some(item => item.children?.some(child => child.key === key));
    },
    [menuItems]
  );

  /**
   * Get open keys for a given pathname
   * @param pathname - Current route pathname
   * @returns Array of parent group keys that should be open
   */
  const getOpenKeysForPath = useCallback(
    (pathname: string): string[] => {
      for (const item of menuItems) {
        if (item.children) {
          const child = item.children.find(c => c.key === pathname);
          if (child) {
            return [item.key];
          }
        }
      }
      return [];
    },
    [menuItems]
  );

  /**
   * Handle menu item click
   * @param key - Menu key that was clicked
   * @param navigate - Navigation function from react-router
   */
  const handleMenuClick = useCallback(
    (key: string, navigate: (path: string) => void): void => {
      if (isLeafNode(key)) {
        navigate(key);
      }
    },
    [isLeafNode]
  );

  return {
    // State
    collapsed,
    openKeys,
    // Actions
    toggleCollapsed,
    setCollapsed,
    setOpenKeys,
    handleMenuClick,
    getOpenKeysForPath,
    isLeafNode,
  };
};
