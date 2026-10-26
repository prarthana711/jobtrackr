// The API sends UTC times without a timezone label, e.g. "2025-01-15T10:00:00".
// Without a label, the browser would read that as LOCAL time and show the wrong day.
export function formatDate(isoString) {
  if (!isoString) return "";
  const hasZone = /(Z|[+-]\d{2}:\d{2})$/.test(isoString);
  const date = new Date(hasZone ? isoString : `${isoString}Z`);
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}