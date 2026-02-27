import React from 'react';
import { Typography } from 'antd';

interface VersionDisplayProps {
  version: string;
}

const VersionDisplay: React.FC<VersionDisplayProps> = ({ version }) => {
  return (
    <Typography.Text
      type="secondary"
      style={{
        textAlign: 'center',
        marginTop: 0,
        fontSize: 12,
        opacity: 0.7,
        display: 'block',
      }}
    >
      v{version}
    </Typography.Text>
  );
};

export default VersionDisplay;
