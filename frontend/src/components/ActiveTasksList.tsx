import React from 'react';
import { Card, List, Button, Typography, Progress, Spin, Tag } from 'antd';
import { StopOutlined } from '@ant-design/icons';
import { getTaskStatusIcon } from './statusUtils';

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

interface ActiveTasksListProps {
  activeTasks: Task[];
  handleCancelTask: (taskId: string) => void;
  formatTaskTime: (isoString: string) => string;
}

const ActiveTasksList: React.FC<ActiveTasksListProps> = React.memo(
  ({ activeTasks, handleCancelTask, formatTaskTime }) => {
    if (activeTasks.length === 0) return null;

    return (
      <Card title="Активные задачи" className="margin-top-space-4">
        <List
          dataSource={activeTasks}
          renderItem={task => (
            <List.Item
              actions={[
                (task.status === 'running' || task.status === 'pending') && (
                  <Button
                    danger
                    size="small"
                    onClick={() => handleCancelTask(task.task_id)}
                    icon={<StopOutlined />}
                  >
                    Отменить
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                avatar={getTaskStatusIcon(task.status)}
                title={
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Typography.Text strong>Задача {task.task_id.split('_')[1]}</Typography.Text>
                      <Tag className={`status-${task.status}`}>
                        {task.status === 'pending' && 'Ожидает'}
                        {task.status === 'running' && 'Выполняется'}
                        {task.status === 'completed' && 'Завершена'}
                        {task.status === 'failed' && 'Ошибка'}
                        {task.status === 'cancelled' && 'Отменена'}
                      </Tag>
                    </div>
                    {task.status === 'running' && <Spin size="small" />}
                    {task.status === 'completed' && (
                      <Progress percent={100} status="success" showInfo={false} size="small" />
                    )}
                    {task.status === 'failed' && (
                      <Progress percent={100} status="exception" showInfo={false} size="small" />
                    )}
                  </div>
                }
                description={
                  <div>
                    <div>Кластер: {task.payload?.cluster_name}</div>
                    <div>Создано: {formatTaskTime(task.created_at)}</div>
                    {task.started_at && <div>Запущено: {formatTaskTime(task.started_at)}</div>}
                    {(task.completed_at || task.status === 'failed') && (
                      <div>Завершено: {formatTaskTime(task.completed_at || '')}</div>
                    )}
                    {task.error && (
                      <div style={{ color: 'var(--error-color)', marginTop: '4px' }}>
                        Ошибка: {task.error}
                      </div>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      </Card>
    );
  }
);

ActiveTasksList.displayName = 'ActiveTasksList';

export default ActiveTasksList;
