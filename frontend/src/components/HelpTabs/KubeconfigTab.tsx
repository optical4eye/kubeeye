import React from 'react';
import { Card, Row, Col, Typography } from 'antd';

const { Title, Paragraph, Text } = Typography;

const KubeconfigSection = ({ title, description, whyImportant, steps, code, language = "yaml" }) => (
  <Row gutter={16} className="help-row-margin">
    <Col span={24}>
      <Card title={title} aria-label={`Раздел: ${title}`}>
        <Paragraph>
          <Text strong>Описание:</Text> <span dangerouslySetInnerHTML={{__html: description}} />
        </Paragraph>
        <Paragraph>
          <Text strong>Почему важно:</Text> {whyImportant}
        </Paragraph>
        <Paragraph>
          <Text strong>Шаги:</Text> <span dangerouslySetInnerHTML={{__html: steps}} />
        </Paragraph>
        <div role="code" aria-label={`Пример кода на ${language === "yaml" ? "YAML" : language === "bash" ? "Bash" : "YAML"}`}>
          <pre><code>{code}</code></pre>
        </div>
      </Card>
    </Col>
  </Row>
);

const KubeconfigTab = () => {
  return (
    <>
      <Row gutter={16}>
        <Col span={24}>
          <Title level={3} id="kubeconfig-title">Настройка Kubeconfig для KubeEye</Title>
          <Paragraph>
            Ниже приведены подробные инструкции по настройке kubeconfig для безопасного доступа KubeEye к кластеру Kubernetes. Включает создание read-only ролей, привязок и примеры команд.
          </Paragraph>
        </Col>
      </Row>

      <KubeconfigSection
        title="Получение токена ServiceAccount"
        description="Токен ServiceAccount используется для аутентификации в kubeconfig."
        whyImportant="Токен обеспечивает безопасный доступ без использования статических учетных данных."
        steps="<br />1. Создайте ServiceAccount<br />2. Получите токен<br />3. Используйте токен в kubeconfig."
        code={`# Создание ServiceAccount
kubectl create serviceaccount kubeeye-sa

# Получение токена
kubectl get secret $(kubectl get sa kubeeye-sa -o jsonpath='{.secrets[0].name}') -o jsonpath='{.data.token}' | base64 --decode`}
        language="bash"
      />

      <KubeconfigSection
        title="Введение в Kubeconfig"
        description="Kubeconfig — это файл конфигурации, содержащий информацию о кластерах Kubernetes, пользователях и контекстах. Он необходим для аутентификации и авторизации при подключении к кластеру.<br />
        Чтобы получить certificate-authority-data, выполните команду: <code>kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}</code>"
        whyImportant="Для KubeEye требуется kubeconfig с read-only доступом, чтобы инспектировать кластер без возможности внесения изменений, обеспечивая безопасность и соответствие принципам наименьших привилегий."
        steps="Ознакомьтесь с предпосылками: доступ к кластеру, установленный kubectl, права администратора."
        code={`# Пример структуры kubeconfig
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: <base64-encoded-ca-cert>
    server: https://<cluster-api-server>:6443
  name: my-cluster
contexts:
- context:
    cluster: my-cluster
    user: kubeeye-user
  name: kubeeye-context
current-context: kubeeye-context
users:
- name: kubeeye-user
  user:
    token: <service-account-token>`}
      />

      <KubeconfigSection
        title="Создание ClusterRole (Read Only)"
        description="ClusterRole определяет набор разрешений для доступа к ресурсам Kubernetes на уровне кластера."
        whyImportant="Read-only роль обеспечивает, что KubeEye может только читать ресурсы, не изменяя их, что предотвращает случайные модификации кластера."
        steps="<br />1. Создайте YAML файл с определением ClusterRole.<br />2. Примените его с помощью kubectl apply."
        code={`apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kubeeye-readonly
rules:
- apiGroups: [""]
  resources: ["pods", "services", "endpoints", "nodes", "namespaces", "configmaps", "secrets", "persistentvolumes", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "daemonsets", "statefulsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies", "ingresses"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["clusterroles", "clusterrolebindings", "roles", "rolebindings"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["policy"]
  resources: ["podsecuritypolicies", "poddisruptionbudgets"]
  verbs: ["get", "list", "watch"]`}
      />

      <KubeconfigSection
        title="Создание ClusterRoleBinding"
        description="ClusterRoleBinding связывает ClusterRole с субъектом (ServiceAccount, пользователь или группа)."
        whyImportant="Привязка роли к ServiceAccount позволяет KubeEye аутентифицироваться в кластере с ограниченными правами."
        steps="<br />1. Создайте YAML файл с ClusterRoleBinding.<br />2. Укажите ServiceAccount и ClusterRole.<br />3. Примените с kubectl apply."
        code={`apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubeeye-readonly-binding
subjects:
- kind: ServiceAccount
  name: kubeeye-sa
  namespace: default
roleRef:
  kind: ClusterRole
  name: kubeeye-readonly
  apiGroup: rbac.authorization.k8s.io`}
      />



      <Row gutter={16} className="help-row-margin">
        <Col span={24}>
          <Card title="Советы по безопасности и устранению ошибок" aria-label="Советы по безопасности">
            <Paragraph>
              <Text strong>Необходимые разрешения:</Text> ClusterRole с verbs: get, list, watch; ClusterRoleBinding; доступ к API сервера.
            </Paragraph>
            <Paragraph>
              <Text strong>Советы по устранению ошибок:</Text><br />
              - Ошибка аутентификации: Проверьте токен и CA сертификат.<br />
              - Forbidden: Убедитесь в правильности ClusterRoleBinding.<br />
              - Подключение: Проверьте адрес API сервера.
            </Paragraph>
            <Paragraph>
              <Text strong>Советы по безопасности:</Text><br />
              - Используйте read-only роли.<br />
              - Не делитесь kubeconfig.<br />
              - Ротируйте токены регулярно.<br />
              - Мониторьте логи доступа.
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </>
  );
};

export default KubeconfigTab;