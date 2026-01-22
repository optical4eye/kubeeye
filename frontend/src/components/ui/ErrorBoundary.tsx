import React from 'react';
import { Result, Button, Alert, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';
import { withTranslation, WithTranslation } from 'react-i18next';

const { Paragraph, Text } = Typography;

interface ErrorBoundaryProps extends WithTranslation {
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
    const { t } = this.props;
    if (this.state.hasError) {
      const { error, errorInfo } = this.state;
      const isDevelopment = process.env.NODE_ENV === 'development';

      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return <FallbackComponent error={error!} resetError={this.resetError} />;
      }

      return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
          <Result
            status="error"
            title={t('errorBoundary.title')}
            subTitle={t('errorBoundary.subtitle')}

            extra={
              <>
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={this.resetError}
                  style={{ marginRight: 8 }}
                >
                  {t('errorBoundary.retryButton')}
                </Button>
                <Button icon={<HomeOutlined />} onClick={() => (window.location.href = '/')}>
                  {t('errorBoundary.homeButton')}
                </Button>
              </>
            }
          />

          {isDevelopment && error && (
            <Alert
              message={t('errorBoundary.errorDetailsTitle')}
              description={
                <div>
                  <Paragraph>
                    <Text strong>{t('errorBoundary.messageLabel')}</Text> {error.message}
                  </Paragraph>
                  <Paragraph>
                    <Text strong>{t('errorBoundary.stackLabel')}</Text>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>{error.stack}</pre>
                  </Paragraph>
                  {errorInfo && (
                    <Paragraph>
                      <Text strong>{t('errorBoundary.componentLabel')}</Text>
                      <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px' }}>
                        {errorInfo.componentStack}
                      </pre>
                    </Paragraph>
                  )}
                </div>
              }
              type="error"
              style={{ marginTop: 16 }}
            />
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default withTranslation()(ErrorBoundary);