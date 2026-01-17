import { ThemeConfig, theme as antdTheme } from 'antd';

export const lightTheme: ThemeConfig = {
  algorithm: antdTheme.defaultAlgorithm,
  cssVar: true,
  token: {
    colorPrimary: '#4A90E2',
    colorSuccess: '#7CB342',
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
    Layout: {
      siderBg: '#339af0',
    },
    Switch: {
      colorPrimary: '#339af0',
      colorPrimaryHover: '#4dabf7',
    },
    Menu: {
      colorBgContainer: '#339af0',
      colorItemBg: '#339af0',
      colorItemBgHover: '#4dabf7',
      colorItemBgSelected: '#4dabf7',
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
    Layout: {
      siderBg: '#339af0',
    },
    Switch: {
      colorPrimary: '#339af0',
      colorPrimaryHover: '#4dabf7',
    },
    Menu: {
      colorBgContainer: '#339af0',
      colorItemBg: '#339af0',
      colorItemBgHover: '#4dabf7',
      colorItemBgSelected: '#4dabf7',
    },
  },
};

export const getThemeConfig = (isDark: boolean): ThemeConfig => {
  return isDark ? darkTheme : lightTheme;
};
