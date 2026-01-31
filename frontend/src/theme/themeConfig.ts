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
