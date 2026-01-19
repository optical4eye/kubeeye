import { useState, useCallback, useEffect } from 'react';

// Hook для generic загрузки данных с паттерном setLoading
export const useDataLoader = <T>(
  loaderFn: () => Promise<T>,
  deps: any[] = []
) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loaderFn();
      setData(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Ошибка загрузки данных';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [loaderFn]);

  // Автоматическая загрузка при изменении deps
  useEffect(() => {
    if (deps.length > 0) {
      load();
    }
  }, deps);

  return { data, loading, error, load };
};