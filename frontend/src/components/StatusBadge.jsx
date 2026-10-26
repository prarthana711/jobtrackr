import { STATUS_LABELS, STATUS_STYLES } from "../constants.js";

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? STATUS_STYLES.saved
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}