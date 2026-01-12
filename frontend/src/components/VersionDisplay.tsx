import React from 'react';

interface VersionDisplayProps {
  version: string;
}

const VersionDisplay: React.FC<VersionDisplayProps> = ({ version }) => {
  return (
    <div
      style={{
        textAlign: 'center',
        marginTop: '2px',
        fontSize: '12px',
        color: 'var(--text-secondary)',
      }}
    >
      ver. {version}
    </div>
  );
};

export default VersionDisplay;
