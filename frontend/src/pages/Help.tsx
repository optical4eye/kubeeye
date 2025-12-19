import React, { Suspense, lazy } from 'react';
import { Tabs, Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';

const IntroductionTab = lazy(() => import('../components/HelpTabs/IntroductionTab'));
const ExamplesTab = lazy(() => import('../components/HelpTabs/ExamplesTab'));
const SecurityTab = lazy(() => import('../components/HelpTabs/SecurityTab'));
const KubeconfigTab = lazy(() => import('../components/HelpTabs/KubeconfigTab'));

const Help = () => {
  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        Помощь
      </div>
      <div className="page-subtitle">Руководство по использованию KubeEye и примеры правил</div>

      <Tabs defaultActiveKey="1" aria-label="Разделы справки KubeEye">
        <Tabs.TabPane tab="Введение в Open Policy Agent" key="1" aria-label="Введение в OPA">
          <Suspense fallback={<Spin />}>
            <IntroductionTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Примеры правил" key="2" aria-label="Примеры правил инспекции">
          <Suspense fallback={<Spin />}>
            <ExamplesTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Запрещенные команды" key="3" aria-label="Безопасность и запрещенные команды">
          <Suspense fallback={<Spin />}>
            <SecurityTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Настройка Kubeconfig" key="4" aria-label="Настройка kubeconfig для KubeEye">
          <Suspense fallback={<Spin />}>
            <KubeconfigTab />
          </Suspense>
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default Help;