import React from 'react';
import { Card, List, Button, Typography, Progress, Spin, Tag } from 'antd';
import { StopOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { getTaskStatusIcon, getStatusTag } from '../ui';

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
    const { t } = useTranslation();

    if (activeTasks.length === 0) return null;

    return (
      <Card title={t('tasks.activeTasks')} className="margin-top-space-4">
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
                    {t('tasks.cancel')}
                  </Button>
                ),
              ]}
            >
              <List.Item.Meta
                avatar={getTaskStatusIcon(task.status)}
                title={
                  <div className="active-tasks-list-title">
                    <div className="active-tasks-list-title-row">
                      <Typography.Text strong>
                        {t('tasks.task')} {task.task_id.split('_')[1]}
                      </Typography.Text>
                      {getStatusTag(
                        task.status,
                        (task.status === 'pending' && t('tasks.statusPending')) ||
                          (task.status === 'running' && t('tasks.statusRunning')) ||
                          (task.status === 'completed' && t('tasks.statusCompleted')) ||
                          (task.status === 'failed' && t('tasks.statusFailed')) ||
                          (task.status === 'cancelled' && t('tasks.statusCancelled'))
                      )}
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
                    <div>
                      {t('tasks.cluster')}: {task.payload?.cluster_name}
                    </div>
                    <div>
                      {t('tasks.created')}: {formatTaskTime(task.created_at)}
                    </div>
                    {task.started_at && (
                      <div>
                        {t('tasks.started')}: {formatTaskTime(task.started_at)}
                      </div>
                    )}
                    {(task.completed_at || task.status === 'failed') && (
                      <div>
                        {t('tasks.completed')}: {formatTaskTime(task.completed_at || '')}
                      </div>
                    )}
                    {task.error && (
                      <div className="active-tasks-list-error">
                        {t('tasks.error')}: {task.error}
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
