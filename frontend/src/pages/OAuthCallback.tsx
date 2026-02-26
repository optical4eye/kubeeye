import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import { useAuthStore } from '../stores/authStore';

const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleOAuthCallback } = useAuthStore();
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  const processedRef = React.useRef(false);

  useEffect(() => {
    // Skip if already processed to prevent cascading renders
    if (processedRef.current) return;
    processedRef.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    if (errorParam) {
      queueMicrotask(() => {
        setError(errorDescription || `Authentication error: ${errorParam}`);
        setLoading(false);
      });
      return;
    }

    if (!code || !state) {
      queueMicrotask(() => {
        setError('Missing authorization parameters');
        setLoading(false);
      });
      return;
    }

    handleOAuthCallback(code, state)
      .then(() => {
        navigate('/');
      })
      .catch((err: any) => {
        const errorMsg = err.response?.data?.detail || 'Authentication failed';
        queueMicrotask(() => {
          setError(errorMsg);
          setLoading(false);
        });
      });
  }, [searchParams, navigate, handleOAuthCallback]);

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <Spin size="large" />
        <div>Completing authentication...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Result
          status="error"
          title="Authentication Failed"
          subTitle={error}
          extra={[
            <Button type="primary" key="login" onClick={() => navigate('/login')}>
              Back to Login
            </Button>,
          ]}
        />
      </div>
    );
  }

  return null;
};

export default OAuthCallback;
