import React from 'react';
import { Result, Button } from 'antd';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Что-то пошло не так"
          subTitle="Произошла ошибка при загрузке страницы. Попробуйте перезагрузить страницу."
          extra={
            <Button
              type="primary"
              onClick={() => window.location.reload()}
            >
              Перезагрузить страницу
            </Button>
          }
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;