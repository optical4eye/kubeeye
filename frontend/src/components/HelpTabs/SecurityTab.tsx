import React from 'react';
import { Card, Row, Col, Typography, Divider } from 'antd';
import { SAFE_COMMANDS } from './constants';

const { Title, Paragraph, Text } = Typography;

const CommandList = ({ title, commands, description }) => (
  <>
    <Title level={4}>{title}</Title>
    {description && <Paragraph>{description}</Paragraph>}
    <ul>
      {commands.map((item, index) => (
        <li key={index}>
          <Text strong>{item.category}:</Text> <code>{item.commands}</code>
        </li>
      ))}
    </ul>
  </>
);

const SecurityTab = () => {
  return (
    <Row gutter={16} className="help-row-margin">
      <Col span={24}>
        <Card title="Разрешенные команды" aria-label="Информация о безопасности команд">
          <Paragraph>
            <Text strong>Обзор:</Text> KubeEye — это инструмент для инспекции кластеров Kubernetes,
            который должен работать в режиме только чтения. Для обеспечения безопасности и
            предотвращения несанкционированных изменений в системе, бэкенд KubeEye строго
            ограничивает выполнение команд, которые могут модифицировать систему или данные.
          </Paragraph>
          <Paragraph>
            Все правила выполняются в безопасной среде, где запрещены любые операции модификации.
            Это гарантирует, что инструмент может только наблюдать и анализировать состояние
            кластера, не изменяя его.
          </Paragraph>

          <Divider />

          <Title level={4} id="kubernetes-connection">
            Подключение к Kubernetes
          </Title>
          <Paragraph>
            <Text strong>Read-Only режим:</Text> KubeEye подключается к кластерам Kubernetes
            исключительно в режиме чтения. Все API-вызовы ограничены операциями получения информации
            (list, get, describe), без возможности создания, обновления или удаления ресурсов.
          </Paragraph>
          <Paragraph>
            <Text strong>Безопасность подключения:</Text> Инструмент не имеет прав на модификацию
            кластера и не может выполнять kubectl команды, изменяющие состояние (apply, create,
            delete, edit и т.д.). Разрешены только команды наблюдения: get, describe, logs, explain,
            api-resources, api-versions, version, cluster-info.
          </Paragraph>

          <Paragraph>
            <Text strong>Принцип работы:</Text> Что не разрешено, то запрещено. KubeEye строго
            ограничивает выполнение команд только теми, которые перечислены ниже. Любые другие
            команды будут заблокированы для обеспечения безопасности.
          </Paragraph>

          <Divider />

          <CommandList
            title="Полный список разрешенных команд"
            description="Ниже приведен полный список категорий разрешенных команд. Только эти команды могут быть использованы в правилах KubeEye:"
            commands={SAFE_COMMANDS}
          />

          <Paragraph>
            <Text strong>Пример безопасного правила:</Text> Используйте команды вроде{' '}
            <code>{`df -h / | tail -1 | awk '{print $5}' | sed 's/%//'`}</code> для проверки
            использования диска, которая только читает данные без каких-либо изменений.
          </Paragraph>
        </Card>
      </Col>
    </Row>
  );
};

export default SecurityTab;
