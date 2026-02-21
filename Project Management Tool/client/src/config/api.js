const rawBaseUrl = process.env.REACT_APP_API_BASE_URL || '';
const trimmedBaseUrl = rawBaseUrl.trim().replace(/\/+$/, '');

export function apiUrl(path) {
  const normalizedPath = String(path || '').startsWith('/') ? String(path) : `/${String(path || '')}`;
  return `${trimmedBaseUrl}${normalizedPath}`;
}
