import React, { useState } from 'react';
import { Form, Input, Button, Card, App, Typography, Tooltip } from 'antd';
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

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { message } = App.useApp();
  const { theme: uiTheme } = useUIStore();

  const onFinish = async (values: LoginFormData) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
      message.success('Login successful');
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

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
              <Tooltip title="Enter your registered username">
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
              <Tooltip title="Enter your account password">
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
