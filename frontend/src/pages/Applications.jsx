import { Link } from "react-router";
import { api } from "../api.js";
import ApplicationCard from "../components/ApplicationCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { STATUS_ORDER } from "../constants.js";
import { useQuery } from "../hooks.js";

export default function Applications() {
  const { data, error, loading, reload } = useQuery("applications", () => api.listApplications());
  const remindersQuery = useQuery("reminders", () => api.listReminders({ status: "pending" }));
  const applications = data?.items ?? [];

  // Sort the applications into one list per stage
  const columns = Object.fromEntries(STATUS_ORDER.map((status) => [status, []]));
  for (const application of applications) columns[application.status]?.push(application);

  // Group the pending reminders by the application they belong to
  const remindersByApplication = {};
  for (const reminder of remindersQuery.data ?? []) {
    (remindersByApplication[reminder.application_id] ??= []).push(reminder);
  }

  const shownError = error || remindersQuery.error;

  return (
    <div>
      <h1 className="text-2xl font-semibold">Application board</h1>

      {shownError && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {shownError}
        </p>
      )}

      {!data && loading && <p className="mt-6 text-slate-500">Loading applications...</p>}

      {data && applications.length === 0 && (
        <p className="mt-6 text-slate-600">
          You are not tracking any jobs yet. Open a job from{" "}
          <Link to="/jobs" className="font-medium text-indigo-600 hover:underline">
            your jobs list
          </Link>{" "}
          and click "Track this job".
        </p>
      )}

      {data && data.total > applications.length && (
        <p className="mt-4 text-sm text-slate-500">
          Showing the newest {applications.length} of {data.total} applications.
        </p>
      )}

      {applications.length > 0 && (
        <div className="mt-4 flex gap-4 overflow-x-auto pb-4">
          {STATUS_ORDER.map((status) => (
            <section key={status} className="w-72 shrink-0 rounded-lg bg-slate-100 p-3">
              <div className="mb-3 flex items-center justify-between">
                <StatusBadge status={status} />
                <span className="text-sm text-slate-500">{columns[status].length}</span>
              </div>
              <ul className="space-y-3">
                {columns[status].map((application) => (
                  <ApplicationCard
                    key={application.id}
                    application={application}
                    onChanged={reload}
                    reminders={remindersByApplication[application.id] ?? []}
                    onRemindersChanged={remindersQuery.reload}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}