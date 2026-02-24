import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, App, Typography, Tooltip, Segmented } from 'antd';
import { UserOutlined, LockOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useUIStore } from '../stores/uiStore';
import KubeEyeLogo from '../components/ui/KubeEyeLogo';
import '../styles/Login.css';

const { Title } = Typography;

interface LoginFormData {
  username: string;
  password: string;
}

type AuthType = 'local' | 'ldap';

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [authType, setAuthType] = useState<AuthType>('ldap');
  const navigate = useNavigate();
  const { login, ldapStatus, fetchLdapStatus } = useAuthStore();
  const { message } = App.useApp();
  const { theme: uiTheme } = useUIStore();

  useEffect(() => {
    fetchLdapStatus();
  }, [fetchLdapStatus]);

  const onFinish = async (values: LoginFormData) => {
    setLoading(true);
    try {
      await login(values.username, values.password, authType);
      message.success('Login successful');
      navigate('/');
    } catch (error: any) {
      const errorData = error.response?.data?.detail;
      let errorMessage = 'Login failed';

      if (typeof errorData === 'string') {
        errorMessage = errorData;
      } else if (Array.isArray(errorData)) {
        // Pydantic validation errors format
        errorMessage = errorData.map((e: any) => e.msg).join(', ');
      } else if (errorData?.message) {
        errorMessage = errorData.message;
      }

      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const authTypeOptions = [
    { label: 'Local', value: 'local' },
    { label: 'LDAP', value: 'ldap', disabled: !ldapStatus?.enabled },
  ];

  return (
    <div className="login-container">
      <Card className="login-card">
        <div className="login-logo-container">
          <KubeEyeLogo
            size={80}
            className={`login-logo ${uiTheme === 'dark' ? 'login-logo-dark' : 'login-logo-light'}`}
          />
        </div>
        <Title level={2} className="login-title">
          KubeEye
        </Title>

        {ldapStatus?.enabled && (
          <div style={{ marginBottom: 24, textAlign: 'center' }}>
            <Segmented
              options={authTypeOptions}
              value={authType}
              onChange={value => setAuthType(value as AuthType)}
              block
            />
          </div>
        )}

        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
          validateTrigger="onChange"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Please input your username!' }]}
            tooltip={
              <Tooltip
                title={
                  authType === 'ldap'
                    ? 'Enter your LDAP username'
                    : 'Enter your registered username'
                }
              >
                <QuestionCircleOutlined />
              </Tooltip>
            }
          >
            <Input prefix={<UserOutlined />} placeholder="Username" autoComplete="username" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Please input your password!' }]}
            tooltip={
              <Tooltip
                title={
                  authType === 'ldap' ? 'Enter your LDAP password' : 'Enter your account password'
                }
              >
                <QuestionCircleOutlined />
              </Tooltip>
            }
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Log in
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
