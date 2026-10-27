/**
 * Timezone & Date Formatting Utilities for SismoWatch
 * Standardized to Hora Legal de Colombia (America/Bogota, COT, UTC-5).
 * Strictly avoids emojis as per user directive.
 */

export function formatBogotaDate(isoString, includeTime = true) {
  if (!isoString) return '--';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '--';

    const options = {
      timeZone: 'America/Bogota',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      ...(includeTime
        ? {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          }
        : {})
    };

    return new Intl.DateTimeFormat('es-CO', options).format(date) + (includeTime ? ' (COT)' : '');
  } catch (err) {
    return String(isoString);
  }
}

export function formatBogotaTimeOnly(isoString) {
  if (!isoString) return '--';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '--';

    const options = {
      timeZone: 'America/Bogota',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    };

    return new Intl.DateTimeFormat('es-CO', options).format(date) + ' COT';
  } catch (err) {
    return String(isoString);
  }
}
