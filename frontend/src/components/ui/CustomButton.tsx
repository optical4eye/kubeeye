import React from 'react';
import { Button, ButtonProps } from 'antd';

interface CustomButtonProps extends ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
}

const CustomButton: React.FC<CustomButtonProps> = ({ variant = 'primary', type, ...props }) => {
  const getButtonType = () => {
    switch (variant) {
      case 'primary':
        return 'primary';
      case 'secondary':
        return 'default';
      case 'danger':
        return 'primary';
      case 'success':
        return 'primary';
      default:
        return type || 'default';
    }
  };

  const getButtonProps = () => {
    const baseProps: ButtonProps = {
      ...props,
      type: getButtonType(),
    };

    if (variant === 'danger') {
      baseProps.danger = true;
    }

    if (variant === 'success') {
      baseProps.style = {
        ...baseProps.style,
        backgroundColor: '#52c41a',
        borderColor: '#52c41a',
      };
    }

    return baseProps;
  };

  return <Button {...getButtonProps()} />;
};

export default CustomButton;
