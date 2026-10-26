// The API sends two kinds of dates:
//   timestamps like "2025-01-15T10:00:00" (UTC, but with no timezone label)
//   plain dates like "2025-01-15" (for example applied_on)
function toDate(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    // A plain date: build it in local time, so it never shifts to another day
    return new Date(`${value}T00:00:00`);
  }
  // A timestamp: without a label the browser would read it as LOCAL time
  const hasZone = /(Z|[+-]\d{2}:\d{2})$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

export function formatDate(value) {
  if (!value) return "";
  return toDate(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// A shorter form for chart labels, like "15 Jan"
export function formatDay(value) {
  if (!value) return "";
  return toDate(value).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

// Only ever use http(s) links as clickable hrefs (the backend checks this too)
export function safeUrl(url) {
  return url && /^https?:\/\//i.test(url) ? url : null;
}