import React from 'react';
import { theme } from 'antd';

interface VersionDisplayProps {
  version: string;
}

const VersionDisplay: React.FC<VersionDisplayProps> = ({ version }) => {
  const { token } = theme.useToken();

  return (
    <div
      style={{
        textAlign: 'center',
        marginTop: '0px',
        fontSize: '12px',
        color: token.colorTextSecondary,
        opacity: 0.7,
      }}
    >
      ver. {version}
    </div>
  );
};

export default VersionDisplay;
