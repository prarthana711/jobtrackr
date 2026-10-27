import { useState } from "react";
import { api } from "../api.js";
import { formatDateTime } from "../format.js";

const QUICK_DAYS = [3, 7, 14];

// 9:00 in the user's own timezone, a number of days from now
function nineAmInDays(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  date.setHours(9, 0, 0, 0);
  return date;
}

// 9:00 in the user's own timezone, on a date picked with <input type="date"> ("2026-11-05")
function nineAmOn(dateString) {
  const [year, month, day] = dateString.split("-").map(Number);
  return new Date(year, month - 1, day, 9, 0, 0, 0);
}

export default function ReminderControl({ applicationId, reminders, onChanged }) {
  const [open, setOpen] = useState(false);
  const [customDate, setCustomDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Runs an action, then reloads the reminders. Returns true if it worked.
  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      onChanged();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function add(when) {
    // toISOString() gives an exact UTC moment, so the server never has to guess a timezone
    const saved = await run(() => api.createReminder(applicationId, when.toISOString()));
    if (saved) {
      setOpen(false);
      setCustomDate("");
    }
  }

  return (
    <div className="mt-3 border-t border-slate-100 pt-2 text-xs">
      {reminders.length > 0 && (
        <ul className="mb-2 space-y-1">
          {reminders.map((reminder) => (
            <li key={reminder.id} className="flex items-center justify-between gap-2 text-slate-600">
              <span>Remind {formatDateTime(reminder.remind_at)}</span>
              <button
                className="text-slate-400 hover:text-red-600"
                disabled={busy}
                onClick={() => run(() => api.deleteReminder(reminder.id))}
              >
                Cancel
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        className="font-medium text-indigo-600 hover:underline"
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        {open ? "Close" : "Add reminder"}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {QUICK_DAYS.map((days) => (
              <button
                key={days}
                className="btn px-2 py-1 text-xs"
                disabled={busy}
                onClick={() => add(nineAmInDays(days))}
              >
                In {days} days
              </button>
            ))}
          </div>
          <div className="flex gap-1.5">
            <input
              type="date"
              aria-label="Reminder date"
              className="field py-1 text-xs"
              value={customDate}
              onChange={(event) => setCustomDate(event.target.value)}
            />
            <button
              className="btn px-2 py-1 text-xs"
              disabled={busy || !customDate}
              onClick={() => add(nineAmOn(customDate))}
            >
              Set
            </button>
          </div>
          <p className="text-slate-400">You will get an email at about 9:00 your time.</p>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-2 rounded-md bg-red-50 px-2 py-1 text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}