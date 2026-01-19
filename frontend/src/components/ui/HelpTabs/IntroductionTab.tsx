import React from 'react';
import { Card, Row, Col, Typography } from 'antd';

const { Paragraph, Text } = Typography;

const IntroductionTab = () => {
  return (
    <>
      <Row gutter={16} className="help-row-margin">
        <Col span={24}>
          <Card
            title="Инструменты инспекции кластеров"
            aria-label="Инструменты инспекции кластеров"
          >
            <Paragraph>
              KubeEye использует различные инструменты для инспекции кластеров Kubernetes,
              обеспечивая автоматизированную проверку конфигураций, выявление потенциальных проблем
              и соблюдение лучших практик безопасности. Ниже описаны основные инструменты,
              интегрированные в систему.
            </Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} className="help-row-margin">
        <Col span={24}>
          <Card title="Open Policy Agent (OPA)" aria-label="Open Policy Agent">
            <Paragraph>
              <Text strong>Open Policy Agent (OPA)</Text> — это инструмент для политик и управления
              доступом в облачных и контейнерных средах, таких как Kubernetes. OPA позволяет
              определять и применять политики безопасности, соответствия и управления ресурсами в
              декларативном виде, используя язык Rego. Он интегрируется с KubeEye для анализа
              кластеров Kubernetes на предмет нарушений правил, обеспечивая автоматизированную
              проверку конфигураций и выявление потенциальных проблем.
            </Paragraph>
            <Paragraph>
              В KubeEye OPA используется для выполнения сложных проверок на основе политик,
              написанных на языке Rego, что позволяет гибко настраивать правила безопасности и
              соответствия стандартам.
            </Paragraph>
            <Paragraph>
              <a
                href="https://github.com/open-policy-agent/opa/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Репозиторий OPA на GitHub
              </a>
            </Paragraph>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} className="help-row-margin">
        <Col span={24}>
          <Card title="Popeye" aria-label="Popeye">
            <Paragraph>
              <Text strong>Popeye</Text> — это инструмент для сканирования кластеров Kubernetes на
              предмет потенциальных проблем, таких как неиспользуемые ресурсы, неправильные
              конфигурации и нарушения лучших практик. Он помогает оптимизировать кластеры и
              улучшить их производительность и безопасность.
            </Paragraph>
            <Paragraph>
              В KubeEye Popeye используется для дополнительной инспекции, дополняя возможности OPA.
            </Paragraph>
            <Paragraph>
              <a
                href="https://github.com/derailed/popeye"
                target="_blank"
                rel="noopener noreferrer"
              >
                Репозиторий Popeye на GitHub
              </a>
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default IntroductionTab;
