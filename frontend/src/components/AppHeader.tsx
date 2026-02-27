import React from 'react';
import { Layout, Button, Breadcrumb, Switch, Select, Flex, Space } from 'antd';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  HomeOutlined,
  SunOutlined,
  MoonOutlined,
} from '@ant-design/icons';
import { MenuItem } from '../types/menu';
import { MenuNavigationState, MenuNavigationActions } from '../types/menu';
import UserMenu from './UserMenu';
import { useUIStore } from '../stores/uiStore';

const { Header } = Layout;

interface AppHeaderProps {
  menuItems: MenuItem[];
  menuNavigation: MenuNavigationState & MenuNavigationActions;
}

const AppHeader: React.FC<AppHeaderProps> = ({ menuItems, menuNavigation }) => {
  const { t } = useTranslation();
  const { theme, setTheme, language, setLanguage } = useUIStore();
  const location = useLocation();

  // Generate breadcrumb items based on current path
  const getBreadcrumbItems = () => {
    const items: any[] = [{ title: <HomeOutlined />, href: '/' }];

    for (const group of menuItems) {
      if (group.children) {
        const child = group.children.find((c: MenuItem) => c.key === location.pathname);
        if (child) {
          items.push({ title: group.label });
          items.push({ title: child.label });
          break;
        }
      }
    }

    return items;
  };

  return (
    <Header className="header-bg">
      <Flex className="header-content" align="center">
        <Flex align="center" gap="small">
          {/* Collapse/Expand button */}
          <Button
            type="text"
            icon={menuNavigation.collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={menuNavigation.toggleCollapsed}
            className="desktop-collapse-button"
          />
        </Flex>

        {/* Breadcrumbs */}
        <Space style={{ marginLeft: 8, marginRight: 8 }}>
          <Breadcrumb items={getBreadcrumbItems()} />
        </Space>

        <div className="header-title">{t('header.title')}</div>

        <Flex justify="flex-end" align="center" gap="middle" style={{ marginLeft: 'auto' }}>
          <UserMenu />
          <Switch
            checked={theme === 'dark'}
            onChange={(checked: boolean) => setTheme(checked ? 'dark' : 'light')}
            checkedChildren={<SunOutlined />}
            unCheckedChildren={<MoonOutlined />}
          />
          <Select
            value={language}
            onChange={(value: string) => setLanguage(value)}
            options={[
              { value: 'ru', label: 'RU' },
              { value: 'en', label: 'EN' },
            ]}
            style={{ width: 60 }}
            size="small"
          />
        </Flex>
      </Flex>
    </Header>
  );
};

export default AppHeader;
