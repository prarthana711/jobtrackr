export const STATUS_LABELS = {
  saved: "Saved",
  applied: "Applied",
  online_assessment: "Online assessment",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

// The order of the columns on the board
export const STATUS_ORDER = Object.keys(STATUS_LABELS);

// Full class names, written out, so Tailwind can find them when it scans the code
export const STATUS_STYLES = {
  saved: "bg-slate-100 text-slate-700",
  applied: "bg-blue-100 text-blue-700",
  online_assessment: "bg-amber-100 text-amber-800",
  interview: "bg-violet-100 text-violet-700",
  offer: "bg-emerald-100 text-emerald-700",
  rejected: "bg-red-100 text-red-700",
};