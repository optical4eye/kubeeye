import type { MessageInstance } from 'antd/es/message/interface';

/**
 * API error types
 */
export interface ApiError {
  response?: {
    status: number;
    data?: {
      detail?: string;
      message?: string;
      error?: string;
    };
  };
  message?: string;
  code?: string;
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * Error handler configuration
 */
interface ErrorHandlerConfig {
  showMessage?: boolean;
  logToConsole?: boolean;
  redirectOnAuthError?: boolean;
  customHandler?: (error: ApiError) => void;
  /** Message API instance from App.useApp() */
  messageApi?: MessageInstance;
}

/**
 * Default error handler configuration
 */
const defaultConfig: ErrorHandlerConfig = {
  showMessage: true,
  logToConsole: true,
  redirectOnAuthError: true,
};

/**
 * Get user-friendly error message from API error
 */
const getErrorMessage = (error: ApiError, t: (key: string) => string): string => {
  // Check for specific error messages from backend
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.response?.data?.error) {
    return error.response.data.error;
  }

  // Check for HTTP status codes
  const status = error.response?.status;
  if (status) {
    switch (status) {
      case 400:
        return t('error.badRequest');
      case 401:
        return t('error.unauthorized');
      case 403:
        return t('error.forbidden');
      case 404:
        return t('error.notFound');
      case 409:
        return t('error.conflict');
      case 422:
        return t('error.validationError');
      case 429:
        return t('error.tooManyRequests');
      case 500:
        return t('error.internalServerError');
      case 502:
        return t('error.badGateway');
      case 503:
        return t('error.serviceUnavailable');
      case 504:
        return t('error.gatewayTimeout');
      default:
        return t('error.unknownError');
    }
  }

  // Check for network errors
  if (error.message?.includes('Network Error')) {
    return t('error.networkError');
  }

  // Default error message
  return error.message || t('error.unknownError');
};

/**
 * Get error severity based on status code
 */
const getErrorSeverity = (error: ApiError): ErrorSeverity => {
  const status = error.response?.status;
  if (!status) return ErrorSeverity.WARNING;

  if (status >= 500) return ErrorSeverity.CRITICAL;
  if (status >= 400) return ErrorSeverity.ERROR;
  return ErrorSeverity.WARNING;
};

/**
 * Log error to console
 */
const logError = (error: ApiError, severity: ErrorSeverity): void => {
  const severityLabel = severity.toUpperCase();
  console.error(`[${severityLabel}] API Error:`, error);
};

/**
 * Handle authentication errors
 */
const handleAuthError = (): void => {
  // Clear auth state
  localStorage.removeItem('auth-storage');
  // Redirect to login
  window.location.href = '/login';
};

/**
 * Centralized API error handler
 */
export const handleApiError = (
  error: ApiError,
  t: (key: string) => string,
  config: ErrorHandlerConfig = {}
): void => {
  const finalConfig = { ...defaultConfig, ...config };

  // Get error details
  const errorMessage = getErrorMessage(error, t);
  const severity = getErrorSeverity(error);

  // Log to console if enabled
  if (finalConfig.logToConsole) {
    logError(error, severity);
  }

  // Handle authentication errors
  if (finalConfig.redirectOnAuthError && error.response?.status === 401) {
    handleAuthError();
    return;
  }

  // Show message to user if enabled
  if (finalConfig.showMessage && finalConfig.messageApi) {
    switch (severity) {
      case ErrorSeverity.INFO:
        finalConfig.messageApi.info(errorMessage);
        break;
      case ErrorSeverity.WARNING:
        finalConfig.messageApi.warning(errorMessage);
        break;
      case ErrorSeverity.ERROR:
      case ErrorSeverity.CRITICAL:
        finalConfig.messageApi.error(errorMessage);
        break;
    }
  }

  // Call custom handler if provided
  if (finalConfig.customHandler) {
    finalConfig.customHandler(error);
  }
};

/**
 * Create an error handler with custom configuration
 */
export const createErrorHandler = (t: (key: string) => string, config: ErrorHandlerConfig = {}) => {
  return (error: ApiError) => handleApiError(error, t, config);
};

/**
 * Check if error is a network error
 */
export const isNetworkError = (error: ApiError): boolean => {
  return !error.response && (error.message?.includes('Network Error') ?? false);
};

/**
 * Check if error is an authentication error
 */
export const isAuthError = (error: ApiError): boolean => {
  return error.response?.status === 401;
};

/**
 * Check if error is a validation error
 */
export const isValidationError = (error: ApiError): boolean => {
  return error.response?.status === 422;
};

/**
 * Check if error is a server error (5xx)
 */
export const isServerError = (error: ApiError): boolean => {
  return error.response?.status !== undefined && error.response.status >= 500;
};
