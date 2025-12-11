import React from 'react';
import { Card, Row, Col, Typography } from 'antd';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { DISK_USAGE_RULE, HOST_NETWORK_RULE } from './constants';

// Custom syntax highlighter style matching the app theme
const customSyntaxStyle = {
  'code[class*="language-"]': {
    color: 'var(--code-color)',
    background: 'var(--background-dark)',
    fontFamily: '"Inconsolata", "Monaco", "Consolas", monospace',
    fontSize: '14px',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
  },
  'pre[class*="language-"]': {
    color: 'var(--text-primary)',
    background: 'var(--background-dark)',
    fontFamily: '"Inconsolata", "Monaco", "Consolas", monospace',
    fontSize: '14px',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
    padding: '16px',
    margin: '0',
    overflow: 'auto',
    borderRadius: '4px',
    border: '1px solid var(--secondary-color)',
  },
  'pre[class*="language-"]::-moz-selection': {
    background: 'var(--background-hover)',
  },
  'pre[class*="language-"] ::-moz-selection': {
    background: 'var(--background-hover)',
  },
  'code[class*="language-"]::-moz-selection': {
    background: 'var(--background-hover)',
  },
  'code[class*="language-"] ::-moz-selection': {
    background: 'var(--background-hover)',
  },
  'pre[class*="language-"]::selection': {
    background: 'var(--background-hover)',
  },
  'pre[class*="language-"] ::selection': {
    background: 'var(--background-hover)',
  },
  'code[class*="language-"]::selection': {
    background: 'var(--background-hover)',
  },
  'code[class*="language-"] ::selection': {
    background: 'var(--background-hover)',
  },
  ':not(pre) > code[class*="language-"]': {
    background: 'var(--background-dark)',
    padding: '0.1em',
    borderRadius: '0.3em',
    whiteSpace: 'normal',
  },
  comment: {
    color: 'var(--placeholder-color)',
  },
  prolog: {
    color: 'var(--placeholder-color)',
  },
  doctype: {
    color: 'var(--placeholder-color)',
  },
  cdata: {
    color: 'var(--placeholder-color)',
  },
  punctuation: {
    color: 'var(--text-secondary)',
  },
  property: {
    color: 'var(--primary-color)',
  },
  tag: {
    color: 'var(--primary-color)',
  },
  constant: {
    color: 'var(--warning-color)',
  },
  symbol: {
    color: 'var(--warning-color)',
  },
  deleted: {
    color: 'var(--error-color)',
  },
  boolean: {
    color: 'var(--success-color)',
  },
  number: {
    color: 'var(--success-color)',
  },
  selector: {
    color: 'var(--code-color)',
  },
  'attr-name': {
    color: 'var(--code-color)',
  },
  string: {
    color: 'var(--highlight-color)',
  },
  char: {
    color: 'var(--highlight-color)',
  },
  builtin: {
    color: 'var(--code-color)',
  },
  inserted: {
    color: 'var(--success-color)',
  },
  operator: {
    color: 'var(--text-secondary)',
  },
  entity: {
    color: 'var(--primary-color)',
    cursor: 'help',
  },
  url: {
    color: 'var(--primary-color)',
  },
  '.language-css .token.string': {
    color: 'var(--highlight-color)',
  },
  '.style .token.string': {
    color: 'var(--highlight-color)',
  },
  variable: {
    color: 'var(--warning-color)',
  },
  atrule: {
    color: 'var(--info-color)',
  },
  'attr-value': {
    color: 'var(--highlight-color)',
  },
  function: {
    color: 'var(--code-color)',
  },
  'class-name': {
    color: 'var(--code-color)',
  },
  keyword: {
    color: 'var(--info-color)',
  },
  regex: {
    color: 'var(--success-color)',
  },
  important: {
    color: 'var(--error-color)',
    fontWeight: 'bold',
  },
  bold: {
    fontWeight: 'bold',
  },
  italic: {
    fontStyle: 'italic',
  },
};

const { Title, Paragraph, Text } = Typography;

const RuleExample = ({ title, description, whyImportant, problems, howToApply, code, language = "yaml" }) => (
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
        <Title level={4}>Код примера ({language === "yaml" ? "YAML" : "YAML с Rego"}):</Title>
        <div role="code" aria-label={`Пример кода на ${language === "yaml" ? "YAML" : "Rego"}`}>
          <SyntaxHighlighter language={language} style={customSyntaxStyle}>
            {code}
          </SyntaxHighlighter>
        </div>
      </Card>
    </Col>
  </Row>
);

const ExamplesTab = () => {
  return (
    <>
      <Row gutter={16}>
        <Col span={24}>
          <Title level={3} id="examples-title">Примеры правил</Title>
          <Paragraph>
            Ниже приведены примеры правил из репозитория KubeEye. Каждое правило включает название, код примера, подробные пояснения о том, что проверяет правило, почему оно важно, какие проблемы выявляет, и как его применять в KubeEye.
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
    </>
  );
};

export default ExamplesTab;