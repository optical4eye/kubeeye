import React from 'react';
import { Tabs } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { IntroductionTab, ExamplesTab, SecurityTab, KubeconfigTab } from '../components/HelpTabs';

const Help = () => {
  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" />
        Помощь
      </div>
      <div className="page-subtitle">Руководство по использованию KubeEye и примеры правил</div>

      <Tabs defaultActiveKey="1" aria-label="Разделы справки KubeEye">
        <Tabs.TabPane tab="Введение в Open Policy Agent" key="1" aria-label="Введение в OPA">
          <IntroductionTab />
        </Tabs.TabPane>

        <Tabs.TabPane tab="Примеры правил" key="2" aria-label="Примеры правил инспекции">
          <ExamplesTab />
        </Tabs.TabPane>

        <Tabs.TabPane tab="Запрещенные команды" key="3" aria-label="Безопасность и запрещенные команды">
          <SecurityTab />
        </Tabs.TabPane>

        <Tabs.TabPane tab="Настройка Kubeconfig" key="4" aria-label="Настройка kubeconfig для KubeEye">
          <KubeconfigTab />
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default Help;