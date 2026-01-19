import { useRef, useEffect } from 'react';
import { message } from 'antd';
import { getInspectionTaskStatus, cancelInspectionTask } from '../services/api';

interface Task {
  task_id: string;
  task_type: string;
  status: string;
  created_at: string;
  payload?: any;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
}

export const useTaskPolling = (
  activeTasks: Task[],
  setActiveTasks: React.Dispatch<React.SetStateAction<Task[]>>
) => {
  const pollingIntervals = useRef<Record<string, NodeJS.Timeout>>({});

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollingIntervals.current).forEach(interval => {
        clearInterval(interval);
      });
      pollingIntervals.current = {};
    };
  }, []);

  const startTaskPolling = (taskId: string) => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
    }

    const interval = setInterval(async () => {
      try {
        const response = await getInspectionTaskStatus(taskId);
        const task = response.data;

        setActiveTasks(prev => prev.map(t => (t.task_id === taskId ? task : t)));

        // Stop polling when task is completed or failed
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollingIntervals.current[taskId]);
          delete pollingIntervals.current[taskId];

          if (task.status === 'completed') {
            message.success(
              `Задача ${taskId} завершена успешно. Отчет доступен в разделе "Отчеты"`
            );

            // Trigger a custom event to notify other components about the new report
            window.dispatchEvent(
              new CustomEvent('newReportAvailable', {
                detail: {
                  taskId,
                  result: task.result,
                },
              })
            );
          } else {
            message.error(`Задача ${taskId} завершилась с ошибкой: ${task.error}`);
          }
        }
      } catch (error: any) {
        // Check if it's a 404 error (task not found)
        if (error.response?.status === 404) {
          message.error(
            `Задача ${taskId} не найдена. Возможно, она была удалена или истек срок действия.`
          );
        } else {
          message.error(`Ошибка при проверке статуса задачи ${taskId}: ${error.message}`);
        }

        clearInterval(pollingIntervals.current[taskId]);
        delete pollingIntervals.current[taskId];

        // Update task status to show error in UI
        setActiveTasks(prev =>
          prev.map(t =>
            t.task_id === taskId ? { ...t, status: 'failed', error: error.message } : t
          )
        );
      }
    }, 5000); // Poll every 5 seconds

    pollingIntervals.current[taskId] = interval;
  };

  const stopTaskPolling = (taskId: string) => {
    if (pollingIntervals.current[taskId]) {
      clearInterval(pollingIntervals.current[taskId]);
      delete pollingIntervals.current[taskId];
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await cancelInspectionTask(taskId);
      stopTaskPolling(taskId);
      setActiveTasks(prev =>
        prev.map(t => (t.task_id === taskId ? { ...t, status: 'cancelled' } : t))
      );
      message.success('Задача отменена');
    } catch {
      message.error('Ошибка отмены задачи');
    }
  };

  return {
    startTaskPolling,
    stopTaskPolling,
    handleCancelTask,
  };
};