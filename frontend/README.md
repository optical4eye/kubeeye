# Улучшенные TypeScript типы для Ant Design v6

Этот модуль содержит улучшенные TypeScript типы для работы с Ant Design v6, включая strict типизацию для ThemeConfig, дизайн-токенов и новых API компонентов.

## Особенности

### 🎨 Расширенная система тем

- **Strict типизация** для всех дизайн-токенов
- **Custom extensions** для дополнительных токенов
- **CSS-in-JS интеграция** с @ant-design/cssinjs
- **Runtime theme switching** без перезагрузки
- **Theme presets** для разных пользовательских ролей

### 📝 Улучшенные типы компонентов

- **Form.useForm API** с полными типами
- **Table.Column** с дополнительными возможностями
- **Modal, Message, Notification API** с улучшенной типизацией
- **Component composition patterns** для сложных UI

### 🔧 Утилиты и хелперы

- **ThemeUtils** - утилиты для работы с темами
- **FormUtils** - расширенные возможности форм
- **TableUtils** - дополнительные функции таблиц
- **Responsive hooks** - адаптивное поведение

## Установка

```bash
npm install antd @ant-design/cssinjs
# или
yarn add antd @ant-design/cssinjs
```

## Использование

### Базовая настройка темы

```typescript
import type { ExtendedThemeConfig } from './types';
import { ConfigProvider } from 'antd';

const customTheme: ExtendedThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
    // Custom токены
    customColors: {
      colorBrand: '#001529',
      colorAccent: '#40a9ff',
    },
  },
  components: {
    Button: {
      borderRadius: 4,
    },
  },
  custom: {
    cssinjs: {
      hashed: true,
      prefix: 'my-app',
    },
  },
};

function App() {
  return (
    <ConfigProvider theme={customTheme}>
      {/* Ваше приложение */}
    </ConfigProvider>
  );
}
```

### Использование улучшенных форм

```typescript
import type { UseExtendedFormReturn } from './types';

interface UserForm {
  name: string;
  email: string;
  age: number;
}

function UserFormComponent() {
  const form: UseExtendedFormReturn<UserForm> = useExtendedForm();

  // Автосохранение каждые 30 секунд
  form.autoSave(30000);

  return (
    <Form form={form.form}>
      <Form.Item name="name" rules={[{ required: true }]}>
        <Input />
      </Form.Item>
      <Form.Item name="email" rules={[{ type: 'email' }]}>
        <Input />
      </Form.Item>
    </Form>
  );
}
```

### Расширенные колонки таблиц

```typescript
import type { ExtendedColumnType } from './types';

interface User {
  id: number;
  name: string;
  email: string;
  status: 'active' | 'inactive';
}

const columns: ExtendedColumnType<User>[] = [
  {
    title: 'Имя',
    dataIndex: 'name',
    searchable: true,
    exportable: true,
  },
  {
    title: 'Email',
    dataIndex: 'email',
    customFilter: {
      type: 'input',
      placeholder: 'Поиск по email',
    },
  },
  {
    title: 'Статус',
    dataIndex: 'status',
    customFilter: {
      type: 'select',
      options: [
        { label: 'Активен', value: 'active' },
        { label: 'Неактивен', value: 'inactive' },
      ],
    },
  },
];
```

### CSS-in-JS интеграция

```typescript
import { useCSSInJS } from './hooks';

function StyledComponent() {
  const { createStyle, createCSSVars } = useCSSInJS();

  const styles = createStyle((theme) => ({
    container: {
      backgroundColor: theme.token.colorBgContainer,
      borderRadius: theme.token.borderRadius,
      padding: theme.token.padding,
    },
    button: {
      color: theme.token.colorPrimary,
      '&:hover': {
        color: theme.token.colorPrimaryHover,
      },
    },
  }));

  return (
    <div className={styles.container}>
      <button className={styles.button}>Кнопка</button>
    </div>
  );
}
```

## API Reference

### ThemeConfig

Расширенная конфигурация темы с дополнительными возможностями:

```typescript
interface ExtendedThemeConfig {
  algorithm?: ExtendedMappingAlgorithm;
  token?: Partial<BaseColorTokens & SizeTokens & CustomThemeTokens>;
  components?: ComponentTokens;
  custom?: CustomThemeTokens;
  cssinjs?: {
    hashed?: boolean;
    prefix?: string;
  };
}
```

### Дизайн-токены

#### BaseColorTokens
Основные цветовые токены для брендинга и состояний.

#### SizeTokens
Токены размеров для отступов, границ и шрифтов.

#### CustomThemeTokens
Дополнительные токены для расширения функциональности.

### Component Tokens

Токены для настройки отдельных компонентов:

```typescript
interface ComponentTokens {
  Button?: {
    colorPrimary?: string;
    borderRadius?: number;
  };
  Input?: {
    borderRadius?: number;
  };
  // ... другие компоненты
}
```

## Миграция с Ant Design v5

### Изменения в ThemeConfig

```typescript
// Ant Design v5
const theme = {
  token: {
    colorPrimary: '#1890ff',
  },
};

// Ant Design v6 с улучшенными типами
import type { ExtendedThemeConfig } from './types';

const theme: ExtendedThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    // Дополнительные strict типы
    customColors: {
      colorBrand: '#001529',
    },
  },
  custom: {
    cssinjs: {
      hashed: true,
    },
  },
};
```

### Новые API компонентов

```typescript
// Form.useForm в v6
import type { UseFormReturn } from './types';

const { form, formRef }: UseFormReturn<UserData> = useForm();

// Table.Column в v6
import type { ColumnType } from './types';

const columns: ColumnType<User>[] = [
  {
    title: 'Имя',
    dataIndex: 'name',
    sorter: true,
    filters: [],
  },
];
```

## Лучшие практики

### 1. Использование strict типов

```typescript
// ✅ Хорошо
const theme: ExtendedThemeConfig = {
  token: {
    colorPrimary: '#1890ff', // Типобезопасно
  },
};

// ❌ Плохо
const theme = {
  token: {
    colorPrimary: '#1890ff', // Нет типизации
  },
};
```

### 2. Кастомные токены

```typescript
const theme: ExtendedThemeConfig = {
  token: {
    // Стандартные токены
    colorPrimary: '#1890ff',
    // Кастомные расширения
    customColors: {
      colorBrand: '#001529',
      colorAccent: '#40a9ff',
    },
  },
};
```

### 3. CSS-in-JS интеграция

```typescript
const theme: ExtendedThemeConfig = {
  custom: {
    cssinjs: {
      hashed: true, // Хэшированные классы
      prefix: 'my-app', // Префикс для CSS переменных
    },
  },
};
```

## Поддержка

- **TypeScript**: 4.5+
- **React**: 18+
- **Ant Design**: 6.0+
- **@ant-design/cssinjs**: 1.0+

## Лицензия

MIT
