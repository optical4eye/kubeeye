import React from 'react';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const Help = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">
        <QuestionCircleOutlined className="help-icon-margin" aria-label="Help icon" />
        {t('help.title')}
      </div>
      <div className="page-subtitle">{t('help.subtitle')}</div>
      <div className="kube-padding-20">
        <p>{t('help.useMenu')}</p>
      </div>
    </div>
  );
};

export default Help;
