import React from 'react';

/**
 * Menu types and interfaces
 */

export interface MenuItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  children?: MenuItem[];
}

export interface MenuGroup extends MenuItem {
  children: MenuItem[];
}

export interface MenuNavigationState {
  collapsed: boolean;
  openKeys: string[];
}

export interface MenuNavigationActions {
  toggleCollapsed: () => void;
  setCollapsed: (collapsed: boolean) => void;
  setOpenKeys: (keys: string[]) => void;
  handleMenuClick: (key: string, navigate: (path: string) => void) => void;
  getOpenKeysForPath: (pathname: string) => string[];
  isLeafNode: (key: string) => boolean;
}
