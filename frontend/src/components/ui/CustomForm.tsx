import React from 'react';
import { Form, FormProps } from 'antd';

interface CustomFormProps<T> extends FormProps<T> {
  variant?: 'default' | 'compact' | 'inline';
}

const CustomForm = <T extends object>({
  variant = 'default',
  layout = 'vertical',
  ...props
}: CustomFormProps<T>) => {
  const getFormProps = (): FormProps<T> => {
    const baseProps: FormProps<T> = {
      ...props,
      layout,
      size: 'middle',
    };

    if (variant === 'compact') {
      baseProps.layout = 'vertical';
      baseProps.style = {
        ...baseProps.style,
        marginBottom: 12,
      };
    }

    if (variant === 'inline') {
      baseProps.layout = 'inline';
    }

    return baseProps;
  };

  return <Form {...getFormProps()} />;
};

export default CustomForm;
