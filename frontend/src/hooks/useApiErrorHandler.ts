import { useCallback } from 'react';

// Типы для ошибок
interface ApiError {
  message: string;
  status?: number;
  details?: any;
}

// Hook для централизованной обработки API ошибок
export const useApiErrorHandler = () => {
  const handleError = useCallback((error: ApiError | Error | any, customMessage?: string) => {
    let message = customMessage || 'Произошла ошибка при выполнении запроса';

    if (error instanceof Error) {
      message = error.message;
    } else if (error?.message) {
      message = error.message;
    } else if (typeof error === 'string') {
      message = error;
    }

    // Здесь можно добавить логику для показа уведомлений, например, toast

    // Пример: если есть toast library, раскомментировать
    // toast.error(message);

    // Можно добавить логику для отправки ошибок в аналитику или логи
  }, []);

  return { handleError };
};
