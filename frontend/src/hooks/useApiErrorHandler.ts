import { useCallback } from 'react';
import { message } from 'antd';

// Типы для ошибок
interface ApiError {
  message: string;
  status?: number;
  details?: any;
}

// Hook для централизованной обработки API ошибок
export const useApiErrorHandler = () => {
  const handleError = useCallback((error: ApiError | Error | any, _customMessage?: string) => {
    let customMessage: string;

    if (_customMessage) {
      customMessage = _customMessage;
    } else if (error instanceof Error) {
      customMessage = error.message;
    } else if (error?.message) {
      customMessage = error.message;
    } else if (typeof error === 'string') {
      customMessage = error;
    } else {
      customMessage = 'An unexpected error occurred';
    }

    // Логирование ошибки в консоль
    console.error('API Error:', customMessage, error);

    // Отображение ошибки через message
    message.error(customMessage);

    // Можно добавить логику для отправки ошибок в аналитику или логи
  }, []);

  return { handleError };
};
