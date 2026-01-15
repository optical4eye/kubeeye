import { ThemeConfig } from 'antd';

export const lightTheme: ThemeConfig = {
  algorithm: undefined, // defaultAlgorithm
  cssVar: true,
  token: {
    colorPrimary: '#4dabf7',
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
    Button: {
      borderRadius: 6,
      controlHeight: 32,
      fontSize: 14,
    },
    Table: {
      borderRadius: 6,
      headerBg: '#fafafa',
      rowHoverBg: '#f5f5f5',
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
  },
};

export const darkTheme: ThemeConfig = {
  algorithm: undefined, // darkAlgorithm will be set in App.tsx
  cssVar: true,
  token: {
    colorPrimary: '#4dabf7',
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
    Button: {
      borderRadius: 6,
      controlHeight: 32,
      fontSize: 14,
    },
    Table: {
      borderRadius: 6,
      headerBg: '#1f1f1f',
      rowHoverBg: '#262626',
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
  },
};

export const getThemeConfig = (isDark: boolean): ThemeConfig => {
  return isDark ? darkTheme : lightTheme;
};
