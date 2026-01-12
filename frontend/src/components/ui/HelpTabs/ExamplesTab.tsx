import React from 'react';
import { Card, Row, Col, Typography } from 'antd';
import { DISK_USAGE_RULE, HOST_NETWORK_RULE, POD_RESOURCES_RULE } from './constants';
import CodeHighlighter from '../CodeHighlighter';

const { Title, Paragraph, Text } = Typography;

const RuleExample = ({
  title,
  description,
  whyImportant,
  problems,
  howToApply,
  code,
  language = 'yaml',
}) => (
  <Row gutter={16} className="help-row-margin">
    <Col span={24}>
      <Card title={title} aria-label={`Пример правила: ${title}`}>
        <Paragraph>
          <Text strong>Описание:</Text> {description}
        </Paragraph>
        <Paragraph>
          <Text strong>Почему важно:</Text> {whyImportant}
        </Paragraph>
        <Paragraph>
          <Text strong>Проблемы, которые выявляет:</Text> {problems}
        </Paragraph>
        <Paragraph>
          <Text strong>Как применять в KubeEye:</Text> {howToApply}
        </Paragraph>
        <div role="code" aria-label={`Пример кода на ${language === 'yaml' ? 'YAML' : 'Rego'}`}>
          <CodeHighlighter code={code} language={language} />
        </div>
      </Card>
    </Col>
  </Row>
);

const ExamplesTab = () => {
  return (
    <>
      <Row gutter={16} className="help-row-margin">
        <Col span={24}>
          <Title level={3} id="examples-title">
            Примеры правил
          </Title>
          <Paragraph>
            Ниже приведены примеры правил из репозитория KubeEye. Каждое правило включает название,
            код примера, подробные пояснения о том, что проверяет правило, почему оно важно, какие
            проблемы выявляет, и как его применять в KubeEye.
          </Paragraph>
        </Col>
      </Row>

      <RuleExample
        title="Правило: Проверка использования диска (node-disk-usage-simple)"
        description="Это правило проверяет использование диска на корневом разделе узла. Оно относится к категории хранения и имеет уровень серьезности 'предупреждение'."
        whyImportant="Высокое использование диска может привести к нехватке места для системных операций, журналов и приложений, что может вызвать сбои в работе кластера."
        problems="Правило обнаруживает, если использование диска превышает 70%, что может указывать на накопление временных файлов, журналов или другие проблемы с хранением."
        howToApply="Правило выполняется на уровне узла с помощью команды df. Если условие не выполняется, генерируется предупреждение с рекомендациями по очистке диска."
        code={DISK_USAGE_RULE}
      />

      <RuleExample
        title="Правило: Проверка использования сети хоста (opa-host-network)"
        description="Это правило OPA проверяет, используют ли Pod'ы сеть хоста. Оно относится к категории безопасности и имеет уровень серьезности 'предупреждение'."
        whyImportant="Использование сети хоста может нарушить изоляцию контейнеров и создать уязвимости безопасности, позволяя Pod'ам напрямую взаимодействовать с сетью узла."
        problems="Правило обнаруживает Pod'ы с hostNetwork: true, что может привести к рискам безопасности, таким как несанкционированный доступ к ресурсам узла или другим Pod'ам."
        howToApply="Правило использует Rego для анализа спецификаций Pod'ов, StatefulSet'ов, DaemonSet'ов и Deployment'ов. Если найдены нарушения, генерируется предупреждение с рекомендациями по использованию Service и Ingress вместо hostNetwork."
        code={HOST_NETWORK_RULE}
      />

      <RuleExample
        title="Правило: Проверка ресурсных лимитов Pod (pod-resources-limits)"
        description="Это правило проверяет, установлены ли ресурсные лимиты (CPU и память) для контейнеров в Pod. Оно относится к категории ресурсов и имеет уровень серьезности 'предупреждение'."
        whyImportant="Ресурсные лимиты предотвращают чрезмерное использование ресурсов одним Pod'ом, обеспечивая стабильность кластера и справедливое распределение ресурсов."
        problems="Правило обнаруживает Pod'ы без установленных ресурсных лимитов, что может привести к неконтролируемому потреблению CPU и памяти, влияя на производительность других приложений."
        howToApply="Правило выполняется на уровне кластера с помощью kubectl и jq для анализа спецификаций Pod'ов. Если найдены нарушения, генерируется предупреждение с рекомендациями по установке limits и requests."
        code={POD_RESOURCES_RULE}
      />
    </>
  );
};

export default ExamplesTab;
