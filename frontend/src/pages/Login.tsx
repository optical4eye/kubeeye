import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, App, Typography, Divider, Collapse } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import KubeEyeLogo from '../components/ui/KubeEyeLogo';
import '../styles/Login.css';

const { Title } = Typography;
const { Panel } = Collapse;

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const {
    login,
    initiateOAuthLogin,
    oauthStatus,
    fetchOAuthStatus
  } = useAuthStore();
  const { message } = App.useApp();

  useEffect(() => {
    fetchOAuthStatus();
  }, [fetchOAuthStatus]);

  // OAuth login handler
  const handleOAuthLogin = async () => {
    setLoading(true);
    try {
      await initiateOAuthLogin();
      // Page will redirect to Dex
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to initiate SSO login');
      setLoading(false);
    }
  };

  // Local login handler (admin only)
  const handleLocalLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('Login successful');
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Login failed');
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card">
        <div className="login-logo-container">
          <KubeEyeLogo size={80} />
        </div>
        <Title level={2} className="login-title">KubeEye</Title>

        {/* Primary: OAuth Login */}
        <Button
          type="primary"
          size="large"
          block
          onClick={handleOAuthLogin}
          loading={loading}
          style={{ marginBottom: 24, height: 48 }}
        >
          Login with SSO
        </Button>

        {/* Secondary: Local Login (collapsed) */}
        <Collapse ghost>
          <Panel header="Admin Login (Local)" key="1">
            <Form
              name="login"
              onFinish={handleLocalLogin}
              autoComplete="off"
              size="large"
            >
              <Form.Item
                name="username"
                rules={[{ required: true, message: 'Please input username' }]}
              >
                <Input prefix={<UserOutlined />} placeholder="Admin Username" />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[{ required: true, message: 'Please input password' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Password"
                />
              </Form.Item>

              <Form.Item>
                <Button type="default" htmlType="submit" loading={loading} block>
                  Login
                </Button>
              </Form.Item>
            </Form>
          </Panel>
        </Collapse>

        {oauthStatus && !oauthStatus.connected && (
          <div style={{ marginTop: 16, color: '#ff4d4f', textAlign: 'center' }}>
            SSO service unavailable. Please use local admin login.
          </div>
        )}
      </Card>
    </div>
  );
};

export default Login;
