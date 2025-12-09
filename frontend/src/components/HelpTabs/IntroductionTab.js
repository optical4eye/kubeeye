import React from 'react';
import { Card, Row, Col, Typography } from 'antd';

const { Paragraph, Text } = Typography;

const IntroductionTab = () => {
  return (
    <Row gutter={16} style={{ marginBottom: 24 }}>
      <Col span={24}>
        <Card title="Введение в Open Policy Agent (OPA)">
          <Paragraph>
            <Text strong>Open Policy Agent (OPA)</Text> — это инструмент для политик и управления доступом в облачных и контейнерных средах, таких как Kubernetes.
            OPA позволяет определять и применять политики безопасности, соответствия и управления ресурсами в декларативном виде, используя язык Rego.
            Он интегрируется с KubeEye для анализа кластеров Kubernetes на предмет нарушений правил, обеспечивая автоматизированную проверку конфигураций и выявление потенциальных проблем.
          </Paragraph>
          <Paragraph>
            В KubeEye OPA используется для выполнения сложных проверок на основе политик, написанных на языке Rego, что позволяет гибко настраивать правила безопасности и соответствия стандартам.
          </Paragraph>
        </Card>
      </Col>
    </Row>
  );
};

export default IntroductionTab;