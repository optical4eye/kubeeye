import { MenuItem } from '../types/menu';
import {
  DashboardOutlined,
  SearchOutlined,
  FileTextOutlined,
  QuestionCircleOutlined,
  ApartmentOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';

/**
 * Menu configuration
 * Defines all menu items with their structure and icons
 */
export const createMenuItems = (t: (key: string) => string): MenuItem[] => [
  {
    key: 'overview',
    icon: <DashboardOutlined />,
    label: t('menu.groups.overview'),
    children: [
      {
        key: '/',
        label: t('menu.dashboard'),
      },
    ],
  },
  {
    key: 'infrastructure',
    icon: <ApartmentOutlined />,
    label: t('menu.groups.infrastructure'),
    children: [
      {
        key: '/clusters',
        label: t('menu.clusters'),
      },
      {
        key: '/add-cluster',
        label: t('menu.addCluster'),
      },
      {
        key: '/network',
        label: t('menu.network'),
      },
    ],
  },
  {
    key: 'inspections',
    icon: <SearchOutlined />,
    label: t('menu.groups.inspections'),
    children: [
      {
        key: '/inspection',
        label: t('menu.inspection'),
      },
      {
        key: '/scheduled-inspection',
        label: t('menu.scheduledInspection'),
      },
      {
        key: '/popeye',
        label: t('menu.popeye'),
      },
    ],
  },
  {
    key: 'reports',
    icon: <FileTextOutlined />,
    label: t('menu.groups.reports'),
    children: [
      {
        key: '/reports',
        label: t('menu.reports'),
      },
    ],
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: t('menu.groups.settings'),
    children: [
      {
        key: '/rules',
        label: t('menu.rules'),
      },
      {
        key: '/secrets',
        label: t('menu.secrets'),
      },
    ],
  },
  {
    key: 'management',
    icon: <TeamOutlined />,
    label: t('menu.groups.management'),
    children: [
      {
        key: '/users',
        label: t('menu.users'),
      },
      {
        key: '/audit-logs',
        label: t('menu.auditLogs'),
      },
    ],
  },
  {
    key: 'help',
    icon: <QuestionCircleOutlined />,
    label: t('menu.groups.help'),
    children: [
      {
        key: '/help/introduction',
        label: t('menu.helpIntroduction'),
      },
      {
        key: '/help/examples',
        label: t('menu.helpExamples'),
      },
      {
        key: '/help/security',
        label: t('menu.helpSecurity'),
      },
      {
        key: '/help/kubeconfig',
        label: t('menu.helpKubeconfig'),
      },
      {
        key: '/help/api',
        label: t('menu.helpApi'),
      },
    ],
  },
];
