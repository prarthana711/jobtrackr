import { useState } from "react";
import { Link, useParams } from "react-router";
import { api } from "../api.js";
import MatchPanel from "../components/MatchPanel.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { formatDate, safeUrl } from "../format.js";
import { useQuery } from "../hooks.js";

export default function JobDetail() {
  const { jobId } = useParams();
  const jobQuery = useQuery(`job-${jobId}`, () => api.getJob(jobId));
  const applicationsQuery = useQuery("applications", () => api.listApplications());
  const [tracking, setTracking] = useState(false);
  const [trackError, setTrackError] = useState("");

  // Only trust the data if it belongs to this URL's job
  const job = jobQuery.data && String(jobQuery.data.id) === jobId ? jobQuery.data : null;
  const application = applicationsQuery.data?.items.find((item) => item.job_id === Number(jobId));

  async function handleTrack() {
    setTracking(true);
    setTrackError("");
    try {
      await api.trackJob(job.id);
      applicationsQuery.reload();
    } catch (err) {
      setTrackError(err.message);
    } finally {
      setTracking(false);
    }
  }

  if (!job && jobQuery.loading) return <p className="text-slate-500">Loading job...</p>;

  if (!job) {
    return (
      <div>
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {jobQuery.error || "Job not found."}
        </p>
        <Link to="/jobs" className="mt-4 inline-block font-medium text-indigo-600 hover:underline">
          Back to jobs
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link to="/jobs" className="text-sm font-medium text-indigo-600 hover:underline">
        Back to jobs
      </Link>

      <header>
        <h1 className="text-2xl font-semibold">{job.title}</h1>
        <p className="mt-1 text-slate-600">
          {job.company}
          {job.location ? ` · ${job.location}` : ""}
        </p>
        <p className="mt-1 text-xs text-slate-400">Added {formatDate(job.created_at)}</p>
        {safeUrl(job.url) && (
          <a
            className="btn mt-3"
            href={safeUrl(job.url)}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open posting
          </a>
        )}
      </header>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-medium">Application</h2>
        <div className="mt-3">
          {!applicationsQuery.data && applicationsQuery.loading && (
            <p className="text-sm text-slate-500">Loading...</p>
          )}

          {application && (
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={application.status} />
              <Link to="/applications" className="text-sm font-medium text-indigo-600 hover:underline">
                Open the board
              </Link>
            </div>
          )}

          {applicationsQuery.data && !application && (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm text-slate-600">You are not tracking this job yet.</p>
              <button className="btn btn-primary" onClick={handleTrack} disabled={tracking}>
                {tracking ? "Saving..." : "Track this job"}
              </button>
            </div>
          )}

          {(trackError || applicationsQuery.error) && (
            <p role="alert" className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {trackError || applicationsQuery.error}
            </p>
          )}
        </div>
      </section>

      <MatchPanel job={job} />

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="font-medium">Description</h2>
        <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{job.description}</p>
      </section>
    </div>
  );
}