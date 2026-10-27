import { useState } from "react";
import { Link } from "react-router";
import { api } from "../api.js";
import { STATUS_LABELS } from "../constants.js";
import { formatDate } from "../format.js";
import { useQuery } from "../hooks.js";
import ReminderControl from "./ReminderControl.jsx";

function label(status) {
  return STATUS_LABELS[status] ?? status;
}

// Only exists while "History" is open, so the request only runs when you click it
function History({ applicationId }) {
  const { data, error } = useQuery(`history-${applicationId}`, () =>
    api.applicationHistory(applicationId),
  );

  if (error) return <p className="mt-2 text-xs text-red-700">{error}</p>;
  if (!data) return <p className="mt-2 text-xs text-slate-500">Loading...</p>;
  return (
    <ol className="mt-2 space-y-1 text-xs text-slate-600">
      {data.map((entry) => (
        <li key={entry.id}>
          <span className="text-slate-400">{formatDate(entry.changed_at)}</span>{" "}
          {entry.from_status
            ? `${label(entry.from_status)} → ${label(entry.to_status)}`
            : `Added as ${label(entry.to_status)}`}
        </li>
      ))}
    </ol>
  );
}

export default function ApplicationCard({ application, onChanged, reminders = [], onRemindersChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showHistory, setShowHistory] = useState(false);

  // Runs an action, then asks the board to reload. Shows the error if it fails.
  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function handleRemove() {
    const message = `Stop tracking "${application.job.title}"? Its history will be deleted.`;
    if (window.confirm(message)) run(() => api.deleteApplication(application.id));
  }

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <h3 className="font-medium leading-snug">
        <Link to={`/jobs/${application.job_id}`} className="hover:text-indigo-600 hover:underline">
          {application.job.title}
        </Link>
      </h3>
      <p className="text-sm text-slate-600">{application.job.company}</p>
      {application.applied_on && (
        <p className="mt-1 text-xs text-slate-400">Applied {formatDate(application.applied_on)}</p>
      )}

      {/* One button per move the backend allows. The rules live on the server. */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {application.allowed_next.map((next) => (
          <button
            key={next}
            className={`btn px-2 py-1 text-xs ${next === "rejected" ? "btn-danger" : ""}`}
            disabled={busy}
            onClick={() => run(() => api.changeStatus(application.id, next))}
          >
            {next === "rejected" ? "Mark rejected" : `→ ${label(next)}`}
          </button>
        ))}
        {application.allowed_next.length === 0 && (
          <span className="text-xs text-slate-400">Final stage</span>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-2 rounded-md bg-red-50 px-2 py-1 text-xs text-red-700">
          {error}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between text-xs">
        <button
          className="font-medium text-indigo-600 hover:underline"
          onClick={() => setShowHistory((open) => !open)}
        >
          {showHistory ? "Hide history" : "History"}
        </button>
        <button className="text-slate-400 hover:text-red-600" disabled={busy} onClick={handleRemove}>
          Remove
        </button>
      </div>
      {showHistory && <History applicationId={application.id} />}
    </li>
  );
}