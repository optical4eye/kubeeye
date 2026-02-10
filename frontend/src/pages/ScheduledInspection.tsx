import React from 'react';
import { useTranslation } from 'react-i18next';
import { ScheduledInspection } from '../components/tasks';

const ScheduledInspectionPage = () => {
  const { t } = useTranslation();

  return (
    <div>
      <div className="page-title">{t('inspection.scheduled')}</div>
      <div className="page-subtitle">{t('inspection.scheduledSubtitle')}</div>
      <ScheduledInspection />
    </div>
  );
};

export default ScheduledInspectionPage;
