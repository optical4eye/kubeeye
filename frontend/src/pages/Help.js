import React from 'react';
import { Tabs } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { IntroductionTab, ExamplesTab, SecurityTab } from '../components/HelpTabs';

const Help = () => {
  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined style={{ marginRight: 8 }} />
        Помощь
      </div>
      <div className="page-subtitle">Руководство по использованию KubeEye и примеры правил</div>

      <Tabs defaultActiveKey="1">
        <Tabs.TabPane tab="Введение в Open Policy Agent" key="1">
          <IntroductionTab />
        </Tabs.TabPane>

        <Tabs.TabPane tab="Примеры правил" key="2">
          <ExamplesTab />
        </Tabs.TabPane>

        <Tabs.TabPane tab="Запрещенные команды" key="3">
          <SecurityTab />
        </Tabs.TabPane>
      </Tabs>
    </div>
  );
};

export default Help;