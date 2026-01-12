/**
 * MaskedInput component for secure password/secret input
 * Features:
 * - Auto-hide after 30 seconds
 * - Toggle visibility button
 * - Copy to clipboard
 * - Security warning
 */

import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, Tooltip, message } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined, CopyOutlined, LockOutlined } from '@ant-design/icons';
import './MaskedInput.css';

interface MaskedInputProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  autoHide?: boolean;
  hideDelay?: number; // seconds
  allowCopy?: boolean;
  showWarning?: boolean;
  className?: string;
  type?: 'password' | 'text';
}

const MaskedInput: React.FC<MaskedInputProps> = ({
  value = '',
  onChange,
  placeholder = '••••••••',
  disabled = false,
  autoHide = true,
  hideDelay = 30,
  allowCopy = true,
  showWarning = true,
  className = '',
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [timeLeft, setTimeLeft] = useState(hideDelay);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-hide timer
  useEffect(() => {
    if (isVisible && autoHide) {
      // Start countdown
      countdownRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            setIsVisible(false);
            return hideDelay;
          }
          return prev - 1;
        });
      }, 1000);

      // Auto-hide after delay
      timerRef.current = setTimeout(() => {
        setIsVisible(false);
      }, hideDelay * 1000);
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
      }
    };
  }, [isVisible, autoHide, hideDelay]);

  const toggleVisibility = () => {
    setIsVisible(!isVisible);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setIsCopied(true);
      message.success('Скопировано в буфер обмена');
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      message.error('Не удалось скопировать');
    }
  };

  const suffix = (
    <div className="masked-input-suffix">
      {allowCopy && value && (
        <Tooltip title={isCopied ? 'Скопировано' : 'Копировать'}>
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={handleCopy}
            className="masked-input-button"
          />
        </Tooltip>
      )}
      <Tooltip title={isVisible ? 'Скрыть' : 'Показать'}>
        <Button
          type="text"
          icon={isVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
          onClick={toggleVisibility}
          className="masked-input-button"
        />
      </Tooltip>
    </div>
  );

  return (
    <div className={`masked-input-container ${className}`}>
      <Input.Password
        value={value}
        onChange={e => onChange?.(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        visibilityToggle={false}
        suffix={suffix}
        className="masked-input"
        type={isVisible ? 'text' : 'password'}
      />
      {showWarning && isVisible && (
        <div className="masked-input-warning">
          <LockOutlined />
          <span>Данные будут скрыты через {timeLeft} сек. для безопасности</span>
        </div>
      )}
    </div>
  );
};

export default MaskedInput;
