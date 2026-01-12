import React, { Suspense, lazy } from 'react';
import { Tabs, Spin } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';

const IntroductionTab = lazy(() => import('../components/ui/HelpTabs/IntroductionTab'));
const ExamplesTab = lazy(() => import('../components/ui/HelpTabs/ExamplesTab'));
const SecurityTab = lazy(() => import('../components/ui/HelpTabs/SecurityTab'));
const KubeconfigTab = lazy(() => import('../components/ui/HelpTabs/KubeconfigTab'));
const ApiTab = lazy(() => import('../components/ui/HelpTabs/ApiTab'));

const Help = () => {
  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        Помощь
      </div>
      <div className="page-subtitle">Руководство по использованию KubeEye и примеры правил</div>

      <Tabs defaultActiveKey="1" aria-label="Разделы справки KubeEye">
        <Tabs.TabPane
          tab="Инструменты инспекции кластеров"
          key="1"
          aria-label="Инструменты инспекции кластеров"
        >
          <Suspense fallback={<Spin />}>
            <IntroductionTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Примеры правил" key="2" aria-label="Примеры правил инспекции">
          <Suspense fallback={<Spin />}>
            <ExamplesTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane
          tab="Разрешенные команды"
          key="3"
          aria-label="Безопасность и разрешенные команды"
        >
          <Suspense fallback={<Spin />}>
            <SecurityTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane
          tab="Настройка Kubeconfig"
          key="4"
          aria-label="Настройка kubeconfig для KubeEye"
        >
          <Suspense fallback={<Spin />}>
            <KubeconfigTab />
          </Suspense>
        </Tabs.TabPane>

        <Tabs.TabPane tab="API" key="5" aria-label="Документация API KubeEye">
          <Suspense fallback={<Spin />}>
            <ApiTab />
          </Suspense>
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default Help;
