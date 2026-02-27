import React from 'react';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { Space } from 'antd';

const Help = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.title')}
      </div>
      <div className="page-subtitle">{t('help.subtitle')}</div>
      <Space direction="vertical" style={{ padding: 20, width: '100%' }}>
        <p>{t('help.useMenu')}</p>
      </Space>
    </div>
  );
};

export default Help;
