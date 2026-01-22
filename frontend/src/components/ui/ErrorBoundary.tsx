import React from 'react';
import { Result, Button, Alert, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });

    // Log error to monitoring service
    this.logError(error, errorInfo);

    console.error('Error caught by boundary:', error, errorInfo);
  }

  logError = (error: Error, errorInfo: React.ErrorInfo) => {
    // In a real app, send to error monitoring service like Sentry
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    // For now, just console.error in production, could send to API
    if (process.env.NODE_ENV === 'production') {
      // TODO: Send to error monitoring service
      console.error('Error report:', errorReport);
    }
  };

  resetError = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo } = this.state;
      const isDevelopment = process.env.NODE_ENV === 'development';

      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return <FallbackComponent error={error!} resetError={this.resetError} />;
      }

      return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', backgroundColor: 'black', color: 'white', minHeight: '100vh' }}>
          <Result
            status="error"
            title="Что-то пошло не так"
            subTitle="Произошла ошибка при загрузке страницы."
            style={{ color: 'white' }}
            extra={
              <>
                <Button
                  type="default"
                  icon={<ReloadOutlined />}
                  onClick={this.resetError}
                  style={{ marginRight: 8, color: 'white', borderColor: 'white' }}
                >
                  Попробовать снова
                </Button>
                <Button type="default" icon={<HomeOutlined />} onClick={() => (window.location.href = '/')} style={{ color: 'white', borderColor: 'white' }}>
                  На главную
                </Button>
              </>
            }
          />

          {isDevelopment && error && (
            <Alert
              message="Детали ошибки (только в режиме разработки)"
              description={
                <div>
                  <Paragraph style={{ color: 'white' }}>
                    <Text strong style={{ color: 'white' }}>Сообщение:</Text> {error.message}
                  </Paragraph>
                  <Paragraph style={{ color: 'white' }}>
                    <Text strong style={{ color: 'white' }}>Стек:</Text>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px', color: 'white' }}>{error.stack}</pre>
                  </Paragraph>
                  {errorInfo && (
                    <Paragraph style={{ color: 'white' }}>
                      <Text strong style={{ color: 'white' }}>Компонент:</Text>
                      <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px', color: 'white' }}>
                        {errorInfo.componentStack}
                      </pre>
                    </Paragraph>
                  )}
                </div>
              }
              type="error"
              style={{ marginTop: 16, color: 'white', backgroundColor: '#333', borderColor: '#555' }}
            />
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
