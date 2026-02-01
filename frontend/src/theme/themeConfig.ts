import { ThemeConfig, theme as antdTheme } from 'antd';

export const lightTheme: ThemeConfig = {
  algorithm: antdTheme.defaultAlgorithm,
  cssVar: true,
  token: {
    colorPrimary: '#339af0',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#13c2c2',
    colorTextBase: '#000000d9',
    colorBgBase: '#ffffff',
    borderRadius: 6,
    fontSize: 14,
    lineHeight: 1.5715,
    // Custom status tokens
    colorStatusPassed: '#52c41a',
    colorStatusFailed: '#ff4d4f',
    colorStatusWarning: '#faad14',
    colorStatusInfo: '#1890ff',
    colorStatusPending: '#faad14',
    colorStatusRunning: '#1890ff',
    colorStatusSkipped: '#8c8c8c',
    colorStatusUnknown: '#8c8c8c',
    colorStatusError: '#ff4d4f',
    colorStatusSuccess: '#52c41a',
    colorStatusCritical: '#ff4d4f',
    colorStatusHigh: '#ff4d4f',
    colorStatusMedium: '#faad14',
    colorStatusLow: '#1890ff',
    colorStatusOk: '#52c41a',
    colorStatusCompleted: '#52c41a',
    colorStatusCancelled: '#8c8c8c',
    colorStatusEnabled: '#52c41a',
    colorStatusDisabled: '#ff4d4f',
    colorStatusConfigured: '#52c41a',
    colorStatusNotConfigured: '#ff4d4f',
    colorStatusExpired: '#ff4d4f',
    colorStatusExpiresSoon: '#faad14',
    colorStatusValid: '#52c41a',
    colorStatusReady: '#52c41a',
    colorStatusNotReady: '#faad14',
    // Secret type tokens
    colorSecretTypePassword: '#7950f2',
    colorSecretTypeSshKey: '#15aabf',
    colorSecretTypeKubeconfig: '#be4bdb',
    colorSecretTypeDefault: '#4c6ef5',
    // Inspection rule tags
    colorInspectionRuleTags: '#7950f2',
  },
  components: {
    Alert: {
      colorInfoBg: 'transparent',
      colorInfoBorder: '#339af0',
    },
    Button: {
      borderRadius: 6,
      controlHeight: 32,
      fontSize: 14,
    },
    Table: {
      borderRadius: 6,
      headerBg: '#fafafa',
      rowHoverBg: 'rgba(51, 154, 240, 0.08)',
    },
    Form: {
      itemMarginBottom: 16,
      verticalLabelPadding: '0 0 8px',
    },
    Checkbox: {
      borderRadius: 4,
    },
    Message: {
      borderRadius: 6,
    },
    Card: {
      borderRadius: 6,
      boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)',
    },
    Layout: {
      siderBg: 'var(--ant-color-bg-elevated)',
    },
    Switch: {
      colorPrimary: '#339af0',
      colorPrimaryHover: '#4dabf7',
    },
    Menu: {
      colorBgContainer: 'var(--ant-color-bg-elevated)',
      colorItemBg: 'transparent',
      colorItemBgHover: 'rgba(51, 154, 240, 0.08)',
      colorItemBgSelected: 'rgba(51, 154, 240, 0.15)',
      colorItemText: 'var(--ant-color-text)',
      colorItemTextSelected: 'var(--ant-color-primary)',
      colorItemTextHover: 'var(--ant-color-primary)',
    },
  },
};

export const darkTheme: ThemeConfig = {
  algorithm: antdTheme.darkAlgorithm,
  cssVar: true,
  token: {
    colorPrimary: '#339af0',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#13c2c2',
    colorTextBase: '#ffffffd9',
    colorBgBase: '#141414',
    borderRadius: 6,
    fontSize: 14,
    lineHeight: 1.5715,
    // Custom status tokens
    colorStatusPassed: '#52c41a',
    colorStatusFailed: '#ff4d4f',
    colorStatusWarning: '#faad14',
    colorStatusInfo: '#1890ff',
    colorStatusPending: '#faad14',
    colorStatusRunning: '#1890ff',
    colorStatusSkipped: '#8c8c8c',
    colorStatusUnknown: '#8c8c8c',
    colorStatusError: '#ff4d4f',
    colorStatusSuccess: '#52c41a',
    colorStatusCritical: '#ff4d4f',
    colorStatusHigh: '#ff4d4f',
    colorStatusMedium: '#faad14',
    colorStatusLow: '#1890ff',
    colorStatusOk: '#52c41a',
    colorStatusCompleted: '#52c41a',
    colorStatusCancelled: '#8c8c8c',
    colorStatusEnabled: '#52c41a',
    colorStatusDisabled: '#ff4d4f',
    colorStatusConfigured: '#52c41a',
    colorStatusNotConfigured: '#ff4d4f',
    colorStatusExpired: '#ff4d4f',
    colorStatusExpiresSoon: '#faad14',
    colorStatusValid: '#52c41a',
    colorStatusReady: '#52c41a',
    colorStatusNotReady: '#faad14',
    // Secret type tokens
    colorSecretTypePassword: '#7950f2',
    colorSecretTypeSshKey: '#15aabf',
    colorSecretTypeKubeconfig: '#be4bdb',
    colorSecretTypeDefault: '#4c6ef5',
    // Inspection rule tags
    colorInspectionRuleTags: '#7950f2',
  },
  components: {
    Alert: {
      colorInfoBg: 'transparent',
      colorInfoBorder: '#339af0',
    },
    Button: {
      borderRadius: 6,
      controlHeight: 32,
      fontSize: 14,
    },
    Table: {
      borderRadius: 6,
      headerBg: '#1f1f1f',
      rowHoverBg: 'rgba(51, 154, 240, 0.12)',
    },
    Form: {
      itemMarginBottom: 16,
      verticalLabelPadding: '0 0 8px',
    },
    Checkbox: {
      borderRadius: 4,
    },
    Message: {
      borderRadius: 6,
    },
    Card: {
      borderRadius: 6,
      boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)',
    },
    Layout: {
      siderBg: 'var(--ant-color-bg-elevated)',
    },
    Switch: {
      colorPrimary: '#339af0',
      colorPrimaryHover: '#4dabf7',
    },
    Menu: {
      colorBgContainer: 'var(--ant-color-bg-elevated)',
      colorItemBg: 'transparent',
      colorItemBgHover: 'rgba(51, 154, 240, 0.08)',
      colorItemBgSelected: 'rgba(51, 154, 240, 0.15)',
      colorItemText: 'var(--ant-color-text)',
      colorItemTextSelected: 'var(--ant-color-primary)',
      colorItemTextHover: 'var(--ant-color-primary)',
    },
  },
};

export const getThemeConfig = (isDark: boolean): ThemeConfig => {
  return isDark ? darkTheme : lightTheme;
};
