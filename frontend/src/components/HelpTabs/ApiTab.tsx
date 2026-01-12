import React from 'react';
import { Card, Row, Col, Typography, List, Alert } from 'antd';

const { Paragraph, Text, Title } = Typography;

const ApiTab = () => {
  const mainEndpoints = [
    { endpoint: '/', method: 'GET', description: 'Информация об API и доступных endpoints' },
    { endpoint: '/api/info', method: 'GET', description: 'Детальная информация об API' },
    { endpoint: '/api/health', method: 'GET', description: 'Проверка здоровья системы' },
    { endpoint: '/api/health/db', method: 'GET', description: 'Проверка состояния базы данных' },
    { endpoint: '/api/queue/status', method: 'GET', description: 'Статус очереди задач' },
    { endpoint: '/api/queue/tasks', method: 'GET', description: 'Список задач в очереди' },
  ];

  const apiModules = [
    {
      module: 'Clusters',
      endpoint: '/api/clusters',
      description: 'Управление кластерами Kubernetes',
    },
    {
      module: 'Inspection',
      endpoint: '/api/inspection',
      description: 'Запуск инспекций и анализ результатов',
    },
    { module: 'Reports', endpoint: '/api/reports', description: 'Генерация и управление отчетами' },
    { module: 'Rules', endpoint: '/api/rules', description: 'Управление правилами инспекции' },
    {
      module: 'Scheduled Tasks',
      endpoint: '/api/scheduled-tasks',
      description: 'Планирование автоматических инспекций',
    },
    {
      module: 'GitOps',
      endpoint: '/api/gitops',
      description: 'Интеграция с Git для управления правилами',
    },
    { module: 'Cleanup', endpoint: '/api/cleanup', description: 'Очистка данных и отчетов' },
    {
      module: 'Network',
      endpoint: '/api/network-check',
      description: 'Проверка сетевых подключений',
    },
  ];

  return (
    <Row gutter={16} className="help-row-margin">
      <Col span={24}>
        <Card title="API KubeEye" aria-label="Документация API KubeEye">
          <Paragraph>
            <Text strong>KubeEye API</Text> предоставляет RESTful интерфейс для программного
            взаимодействия с системой инспекции кластеров Kubernetes. API построен на FastAPI и
            поддерживает автоматическую генерацию документации.
          </Paragraph>

          <Alert
            message="Документация API"
            description={
              <div>
                Полная интерактивная документация доступна по адресам:
                <ul style={{ marginTop: '8px', marginBottom: '0' }}>
                  <li>
                    <a href="/docs" target="_blank" rel="noopener noreferrer">
                      Swagger UI (/docs)
                    </a>
                  </li>
                  <li>
                    <a href="/redoc" target="_blank" rel="noopener noreferrer">
                      ReDoc (/redoc)
                    </a>
                  </li>
                  <li>
                    <a href="/openapi.json" target="_blank" rel="noopener noreferrer">
                      OpenAPI JSON (/openapi.json)
                    </a>
                  </li>
                </ul>
              </div>
            }
            type="info"
            showIcon
            style={{ marginBottom: '16px' }}
          />

          <Title level={4}>Основные endpoints</Title>
          <List
            dataSource={mainEndpoints}
            renderItem={item => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <code>
                      {item.method} {item.endpoint}
                    </code>
                  }
                  description={item.description}
                />
              </List.Item>
            )}
            style={{ marginBottom: '16px' }}
          />

          <Title level={4}>Модули API</Title>
          <List
            dataSource={apiModules}
            renderItem={item => (
              <List.Item>
                <List.Item.Meta
                  title={<strong>{item.module}</strong>}
                  description={
                    <div>
                      <code>{item.endpoint}</code> - {item.description}
                    </div>
                  }
                />
              </List.Item>
            )}
          />

          <Paragraph>
            <Text strong>Примечание:</Text> Все операции API являются read-only и не изменяют
            состояние кластеров Kubernetes. API поддерживает CORS для интеграции с веб-приложениями.
          </Paragraph>
        </Card>
      </Col>
    </Row>
  );
};

export default ApiTab;
