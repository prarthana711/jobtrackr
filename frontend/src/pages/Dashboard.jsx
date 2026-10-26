import { Link } from "react-router";
import { api } from "../api.js";
import { STATUS_LABELS } from "../constants.js";
import { formatDay } from "../format.js";
import { useQuery } from "../hooks.js";

// Shows "Loading..." or the error, then calls children(data) once data has arrived
function Loaded({ query, children }) {
  if (query.error && !query.data) {
    return (
      <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
        {query.error}
      </p>
    );
  }
  if (!query.data) return <p className="text-sm text-slate-500">Loading...</p>;
  return children(query.data);
}

function Card({ title, children }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-medium">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" title={hint}>
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function Stats({ funnel }) {
  const reached = (stage) => funnel.stages.find((item) => item.stage === stage)?.count ?? 0;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Stat label="Jobs tracked" value={funnel.total} />
      <Stat label="Applications sent" value={reached("applied")} />
      <Stat
        label="Response rate"
        value={funnel.response_rate === null ? "-" : `${funnel.response_rate}%`}
        hint="Share of sent applications that got any reply, including a rejection"
      />
      <Stat label="Interviews / offers" value={`${reached("interview")} / ${reached("offer")}`} />
    </div>
  );
}

function FunnelChart({ funnel }) {
  if (funnel.total === 0) {
    return (
      <Card title="Application funnel">
        <p className="text-sm text-slate-600">Track a job to see your funnel.</p>
      </Card>
    );
  }
  return (
    <Card title="Application funnel">
      <ul className="space-y-3">
        {funnel.stages.map((stage) => (
          <li key={stage.stage}>
            <div className="flex justify-between text-sm">
              <span>{STATUS_LABELS[stage.stage]}</span>
              <span className="text-slate-500">
                {stage.count} · {stage.percent_of_total}%
              </span>
            </div>
            <div className="mt-1 h-3 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-indigo-500"
                style={{ width: `${stage.count === 0 ? 0 : Math.max(stage.percent_of_total, 2)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-slate-500">
        Rejected at any stage: <span className="font-medium text-slate-700">{funnel.rejected}</span>.
        Each stage counts applications that ever reached it, so one rejected after an interview
        still counts under Interview.
      </p>
    </Card>
  );
}

function WeeklyChart({ weeks }) {
  const max = Math.max(1, ...weeks.map((week) => week.applications));
  const total = weeks.reduce((sum, week) => sum + week.applications, 0);

  return (
    <Card title="Applications sent per week (last 12 weeks)">
      <div className="flex items-end gap-1.5 sm:gap-2">
        {weeks.map((week) => {
          const height = week.applications === 0 ? 0 : Math.max((week.applications / max) * 100, 4);
          return (
            <div key={week.week_start} className="flex min-w-0 flex-1 flex-col items-center gap-1">
              <span className="text-xs text-slate-600">{week.applications}</span>
              <div className="flex h-32 w-full items-end">
                <div className="w-full rounded-t bg-indigo-500" style={{ height: `${height}%` }} />
              </div>
              <span className="w-full truncate text-center text-[10px] text-slate-400">
                {formatDay(week.week_start)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-sm text-slate-500">
        {total} sent in this period. Each bar is a week starting on Monday.
      </p>
    </Card>
  );
}

function WeakSpotsBody({ report }) {
  if (report.jobs_analysed === 0) {
    return (
      <p className="text-sm text-slate-600">
        <Link to="/jobs" className="font-medium text-indigo-600 hover:underline">
          Open a job
        </Link>{" "}
        and run a resume match to see which skills to learn next.
      </p>
    );
  }
  if (report.skills.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        Nothing missing across {report.jobs_analysed} jobs. Nice work.
      </p>
    );
  }
  return (
    <>
      <ul className="space-y-3">
        {report.skills.map((item) => (
          <li key={item.skill}>
            <div className="flex justify-between text-sm">
              <span className="font-medium">{item.skill}</span>
              <span className="text-slate-500">
                missing in {item.missing_in_jobs} of {report.jobs_analysed} jobs
              </span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-red-400"
                style={{ width: `${item.percent_of_jobs}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-slate-500">
        Based on your best-matching resume for each job. The skills at the top are the best things
        to learn or add to your resume next.
      </p>
    </>
  );
}

export default function Dashboard() {
  const funnelQuery = useQuery("funnel", () => api.funnel());
  const weeklyQuery = useQuery("weekly", () => api.weekly(12));
  const weakSpotsQuery = useQuery("weak-spots", () => api.weakSpots(8));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <Loaded query={funnelQuery}>
        {(funnel) => (
          <>
            <Stats funnel={funnel} />
            <FunnelChart funnel={funnel} />
          </>
        )}
      </Loaded>

      <Loaded query={weeklyQuery}>{(weeks) => <WeeklyChart weeks={weeks} />}</Loaded>

      <Loaded query={weakSpotsQuery}>
        {(report) => (
          <Card title="Skills you are missing most often">
            <WeakSpotsBody report={report} />
          </Card>
        )}
      </Loaded>
    </div>
  );
}