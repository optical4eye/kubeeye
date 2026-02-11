import React, { lazy } from 'react';
import HelpPage from '../components/ui/HelpPage';

const SecurityTab = lazy(() => import('../components/ui/HelpTabs/SecurityTab'));

const HelpSecurity = () => {
  return (
    <HelpPage
      titleKey="help.tabs.security"
      subtitleKey="help.securitySubtitle"
      TabComponent={SecurityTab}
    />
  );
};

export default HelpSecurity;
