import React, { useState } from 'react';
import { Dropdown, Avatar, Space, Typography, Button, App, Tooltip } from 'antd';
import { UserOutlined, LogoutOutlined, CheckOutlined, KeyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { tokenStorage } from '../utils/tokenStorage';

const { Text } = Typography;

const UserMenu: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [copied, setCopied] = useState(false);
  const { message } = App.useApp();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const copyToClipboardFallback = (text: string): boolean => {
    // Fallback for browsers that don't support navigator.clipboard
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);
      return successful;
    } catch {
      document.body.removeChild(textArea);
      return false;
    }
  };

  const handleCopyToken = async () => {
    const token = tokenStorage.getAccessToken();
    if (!token) {
      message.warning('No token available');
      return;
    }

    let success = false;

    // Try modern clipboard API first
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(token);
        success = true;
      } catch (err) {
        console.warn('Clipboard API failed, trying fallback:', err);
        success = copyToClipboardFallback(token);
      }
    } else {
      // Fallback for non-secure context
      success = copyToClipboardFallback(token);
    }

    if (success) {
      setCopied(true);
      message.success('JWT token copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } else {
      message.error('Failed to copy token. Please copy manually from browser storage.');
      console.log('Token (copy manually):', token);
    }
  };

  const menuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: (
        <Space direction="vertical" size={0}>
          <Text strong>{user?.username}</Text>
          <Text type="secondary" className="kube-font-size-12">
            {user?.role}
          </Text>
        </Space>
      ),
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'copy-token',
      icon: copied ? <CheckOutlined /> : <KeyOutlined />,
      label: (
        <Tooltip title="Copy JWT token for SwaggerUI authorization">
          <span>Copy API Token</span>
        </Tooltip>
      ),
      onClick: handleCopyToken,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      onClick: handleLogout,
      danger: true,
    },
  ];

  return (
    <Dropdown menu={{ items: menuItems }} placement="bottomRight">
      <Button type="text" icon={<Avatar icon={<UserOutlined />} />}>
        {user?.username}
      </Button>
    </Dropdown>
  );
};

export default UserMenu;
