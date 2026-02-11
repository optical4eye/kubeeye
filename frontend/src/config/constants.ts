/**
 * Application constants
 */

/**
 * Minimum loading time in milliseconds for initial load
 */
export const MIN_LOADING_TIME = 200;

/**
 * WebSocket configuration
 */
export const WEBSOCKET_CONFIG = {
  /** Maximum number of reconnection attempts */
  MAX_RECONNECT_ATTEMPTS: 50,
  /** Base delay for exponential backoff in milliseconds */
  BASE_DELAY: 1000,
  /** Maximum delay for exponential backoff in milliseconds */
  MAX_DELAY: 30000,
  /** Maximum jitter to prevent thundering herd in milliseconds */
  JITTER_MAX: 1000,
} as const;

/**
 * API timeout configurations in milliseconds
 */
export const API_TIMEOUTS = {
  /** Default timeout for most API requests */
  DEFAULT: 30000,
  /** Short timeout for quick requests */
  SHORT: 10000,
  /** Long timeout for operations that may take time */
  LONG: 60000,
  /** Extended timeout for very long operations */
  EXTENDED: 120000,
} as const;

/**
 * React Query cache configuration in milliseconds
 */
export const QUERY_CACHE_CONFIG = {
  /** Default stale time - data is considered fresh for 5 minutes */
  STALE_TIME: 5 * 60 * 1000,
  /** Default garbage collection time - cache is kept for 10 minutes */
  GC_TIME: 10 * 60 * 1000,
  /** Maximum number of retry attempts */
  MAX_RETRY_ATTEMPTS: 3,
} as const;
