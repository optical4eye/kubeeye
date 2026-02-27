import React from 'react';
import { Card, Row, Col, Typography, Alert, Space } from 'antd';

const { Paragraph, Text } = Typography;

const ApiTab = () => {
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
              <Space direction="vertical" size="small">
                <div>Полная интерактивная документация доступна по адресам:</div>
                <ul style={{ marginTop: 8, marginBottom: 0 }}>
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
              </Space>
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        </Card>
      </Col>
    </Row>
  );
};

export default ApiTab;
