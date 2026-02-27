import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import 'dayjs/locale/en';

/**
 * Initialize dayjs locale based on current language
 */
export const initDayjsLocale = (locale: string): void => {
  dayjs.locale(locale === 'ru' ? 'ru' : 'en');
};

/**
 * Format date to locale string using dayjs
 * Replaces new Date().toLocaleString()
 *
 * @param date - Date string, Date object, or dayjs object
 * @param format - Format string (default: 'DD.MM.YYYY HH:mm:ss')
 * @returns Formatted date string
 *
 * @example
 * formatDate('2024-01-15T10:30:00') // '15.01.2024 10:30:00'
 * formatDate(new Date(), 'DD.MM-HH:mm') // '15.01-10:30'
 */
export const formatDate = (
  date: string | Date | number | null | undefined,
  format: string = 'DD.MM.YYYY HH:mm:ss'
): string => {
  if (!date) return '-';
  const d = dayjs(date);
  if (!d.isValid()) return '-';
  return d.format(format);
};

/**
 * Format date for display in tables (short format)
 * Matches the pattern: DD.MM-HH:mm used in Dashboard
 *
 * @param date - Date string or Date object
 * @returns Formatted date string (DD.MM-HH:mm)
 */
export const formatDateShort = (date: string | Date | null | undefined): string => {
  return formatDate(date, 'DD.MM-HH:mm');
};

/**
 * Format date for audit logs and reports (Russian locale format)
 *
 * @param date - Date string or Date object
 * @returns Formatted date string
 */
export const formatDateTimeRu = (date: string | Date | null | undefined): string => {
  return formatDate(date, 'DD.MM.YYYY HH:mm:ss');
};

/**
 * Get ISO string for current time
 * Replaces new Date().toISOString()
 *
 * @returns ISO formatted string
 */
export const getCurrentISOTime = (): string => {
  return dayjs().toISOString();
};

/**
 * Format timestamp for filenames (safe for filesystem)
 * Replaces new Date().toISOString().replace(/[:.]/g, '-')
 *
 * @returns Formatted timestamp string
 */
export const formatTimestampForFilename = (): string => {
  return dayjs().format('YYYY-MM-DD_HH-mm-ss');
};

/**
 * Parse ISO string to dayjs object
 *
 * @param isoString - ISO date string
 * @returns dayjs object
 */
export const parseISODate = (isoString: string | null | undefined) => {
  if (!isoString) return null;
  return dayjs(isoString);
};

/**
 * Check if date is valid
 *
 * @param date - Date to check
 * @returns boolean
 */
export const isValidDate = (date: string | Date | null | undefined): boolean => {
  if (!date) return false;
  return dayjs(date).isValid();
};

/**
 * Sort dates (for charts and lists)
 *
 * @param a - First date
 * @param b - Second date
 * @returns number for sort comparison
 */
export const compareDates = (a: string | Date, b: string | Date): number => {
  return dayjs(a).valueOf() - dayjs(b).valueOf();
};

export default {
  formatDate,
  formatDateShort,
  formatDateTimeRu,
  getCurrentISOTime,
  formatTimestampForFilename,
  parseISODate,
  isValidDate,
  compareDates,
  initDayjsLocale,
};
