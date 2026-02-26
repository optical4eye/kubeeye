import React, { useEffect } from 'react';
import { Layout, Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { MenuItem } from '../types/menu';
import { MenuNavigationState, MenuNavigationActions } from '../types/menu';
import VersionDisplay from './ui/VersionDisplay';

const { Sider } = Layout;

interface SidebarProps {
  menuItems: MenuItem[];
  menuNavigation: MenuNavigationState & MenuNavigationActions;
}

const Sidebar: React.FC<SidebarProps> = ({ menuItems, menuNavigation }) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Auto-open menu group on route change (only when not collapsed)
  useEffect(() => {
    if (!menuNavigation.collapsed) {
      const keys = menuNavigation.getOpenKeysForPath(location.pathname);
      if (keys.length > 0 && !menuNavigation.openKeys.includes(keys[0])) {
        menuNavigation.setOpenKeys(keys);
      }
    }
  }, [location.pathname, menuNavigation]);

  return (
    <Sider
      collapsible
      collapsed={menuNavigation.collapsed}
      onCollapse={menuNavigation.toggleCollapsed}
      trigger={null}
      width={200}
      collapsedWidth={64}
      className="sidebar-sider"
    >
      <div className="logo logo-container">
        {menuNavigation.collapsed ? <span>KE</span> : <span>KubeEye</span>}
      </div>
      {!menuNavigation.collapsed && <VersionDisplay version="3.5.3" />}
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        openKeys={menuNavigation.openKeys}
        onOpenChange={menuNavigation.setOpenKeys}
        items={menuItems}
        onClick={({ key }: { key: string }) => {
          // Only navigate if it's a leaf node (not a group)
          if (menuNavigation.isLeafNode(key)) {
            navigate(key);
          }
        }}
      />
    </Sider>
  );
};

export default Sidebar;
