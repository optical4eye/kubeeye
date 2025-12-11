import React from 'react';
import { Card, Row, Col, Typography, Divider } from 'antd';
import { PROHIBITED_COMMANDS, SAFE_COMMANDS } from './constants';

const { Title, Paragraph, Text } = Typography;

const CommandList = ({ title, commands, description }) => (
  <>
    <Title level={4}>{title}</Title>
    {description && <Paragraph>{description}</Paragraph>}
    <ul>
      {commands.map((item, index) => (
        <li key={index}>
          <Text strong>{item.category}:</Text> {item.commands}
        </li>
      ))}
    </ul>
  </>
);

const SecurityTab = () => {
  return (
    <Row gutter={16} className="help-row-margin">
      <Col span={24}>
        <Card title="Запрещенные команды" aria-label="Информация о безопасности команд">
          <Paragraph>
            <Text strong>Обзор:</Text> KubeEye — это инструмент для инспекции кластеров Kubernetes, который должен работать в режиме только чтения. Для обеспечения безопасности и предотвращения несанкционированных изменений в системе, бэкенд KubeEye строго ограничивает выполнение команд, которые могут модифицировать систему или данные.
          </Paragraph>
          <Paragraph>
            Все правила выполняются в безопасной среде, где запрещены любые операции модификации. Это гарантирует, что инструмент может только наблюдать и анализировать состояние кластера, не изменяя его.
          </Paragraph>

          <Divider />

          <Title level={4} id="kubernetes-connection">Подключение к Kubernetes</Title>
          <Paragraph>
            <Text strong>Read-Only режим:</Text> KubeEye подключается к кластерам Kubernetes исключительно в режиме чтения. Все API-вызовы ограничены операциями получения информации (list, get, describe), без возможности создания, обновления или удаления ресурсов.
          </Paragraph>
          <Paragraph>
            <Text strong>Безопасность подключения:</Text> Инструмент не имеет прав на модификацию кластера и не может выполнять kubectl команды, изменяющие состояние (apply, create, delete, edit и т.д.). Разрешены только команды наблюдения: get, describe, logs, explain, api-resources, api-versions, version, cluster-info.
          </Paragraph>
          <Paragraph>
            <Text strong>Принцип работы:</Text> Как инструмент инспекции, KubeEye анализирует конфигурацию и состояние кластера без внесения изменений, обеспечивая безопасность в production-средах.
          </Paragraph>

          <Divider />

          <CommandList
            title="Список запрещенных команд"
            description="Ниже приведен список категорий запрещенных команд. Эти команды полностью заблокированы для выполнения в правилах KubeEye:"
            commands={PROHIBITED_COMMANDS}
          />

          <Divider />

          <Title level={4} id="reasons-for-ban">Причины запрета</Title>
          <Paragraph>
            <Text strong>Принцип "только чтение":</Text> KubeEye разработан как инструмент инспекции, который должен только анализировать состояние системы, не изменяя его. Любые модифицирующие операции противоречат этому принципу.
          </Paragraph>
          <Paragraph>
            <Text strong>Безопасность кластера:</Text> Запрещенные команды могут привести к непреднамеренным изменениям в конфигурации Kubernetes, повреждению данных или нарушению работы сервисов.
          </Paragraph>
          <Paragraph>
            <Text strong>Предотвращение злоупотреблений:</Text> Ограничение команд предотвращает использование KubeEye для вредоносных действий или несанкционированных изменений в производственной среде.
          </Paragraph>

          <Divider />

          <Title level={4} id="potential-risks">Потенциальные риски использования запрещенных команд</Title>
          <Paragraph>
            <Text strong>Повреждение системы:</Text> Команды вроде rm или dd могут привести к потере данных или неработоспособности узлов кластера.
          </Paragraph>
          <Paragraph>
            <Text strong>Нарушение безопасности:</Text> Изменение прав доступа (chmod, chown) или сетевых настроек может создать уязвимости или нарушить изоляцию.
          </Paragraph>
          <Paragraph>
            <Text strong>Сбои в работе кластера:</Text> Остановка сервисов (systemctl stop) или перезагрузка системы может вызвать downtime приложений.
          </Paragraph>
          <Paragraph>
            <Text strong>Несовместимость с Kubernetes:</Text> Модификация системных настроек может конфликтовать с управлением ресурсами Kubernetes.
          </Paragraph>

          <Divider />

          <CommandList
            title="Рекомендуемые безопасные альтернативы"
            description="Для создания правил используйте только команды чтения и анализа. Вот примеры разрешенных команд:"
            commands={SAFE_COMMANDS}
          />

          <Paragraph>
            <Text strong>Пример безопасного правила:</Text> Используйте команды вроде <code>{`df -h / | tail -1 | awk '{print $5}' | sed 's/%//'`}</code> для проверки использования диска, которая только читает данные без каких-либо изменений.
          </Paragraph>
        </Card>
      </Col>
    </Row>
  );
};

export default SecurityTab;