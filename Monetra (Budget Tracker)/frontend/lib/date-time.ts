export const APP_TIME_ZONE = "Europe/London";

export function formatBackendTimestamp(value: string | null | undefined) {
  if (!value) {
    return "Not available";
  }
  const parsed = new Date(normalizeBackendTimestamp(value));
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("en-GB", { timeZone: APP_TIME_ZONE });
}

function normalizeBackendTimestamp(value: string) {
  const trimmed = value.trim();
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(trimmed)) {
    return `${trimmed}Z`;
  }
  return trimmed;
}
