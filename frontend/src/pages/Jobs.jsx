import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../api.js";
import JobForm from "../components/JobForm.jsx";
import Pagination from "../components/Pagination.jsx";
import { formatDate, safeUrl } from "../format.js";

const PAGE_SIZE = 10;



export default function Jobs() {
  const [searchInput, setSearchInput] = useState(""); // what is typed in the box
  const [search, setSearch] = useState(""); // what we actually send to the API
  const [page, setPage] = useState(1);
  const [result, setResult] = useState({ key: "", data: null, error: "" });
  const [actionError, setActionError] = useState(""); // for failed deletes
  const [showForm, setShowForm] = useState(false);
  const [reloadKey, setReloadKey] = useState(0); // change it to force a refetch

  // "Loading" is not stored, it is worked out: if the latest result does not
  // belong to the current search, page, and reload counter, we are still loading.
  const requestKey = `${search}|${page}|${reloadKey}`;
  const loading = result.key !== requestKey;
  const data = result.data;
  const error = actionError || (loading ? "" : result.error);

  // Debounce: wait 300 ms after the last keystroke before searching
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Fetch whenever the search, page, or reload counter changes
  useEffect(() => {
    let ignore = false; // set to true if this request becomes outdated
    api
      .listJobs({ search, page, pageSize: PAGE_SIZE })
      .then((fresh) => {
        if (ignore) return;
        if (fresh.total > 0 && page > fresh.pages) {
          setPage(fresh.pages); // we just deleted the last job on the last page
          return;
        }
        setResult({ key: requestKey, data: fresh, error: "" });
      })
      .catch((err) => {
        // Keep showing the previous list, and show the error above it
        if (!ignore) {
          setResult((previous) => ({ key: requestKey, data: previous.data, error: err.message }));
        }
      });
    return () => {
      ignore = true;
    };
  }, [search, page, requestKey]);

  function handleCreated() {
    setShowForm(false);
    setActionError("");
    setSearchInput("");
    setSearch("");
    setPage(1);
    setReloadKey((key) => key + 1);
  }

  async function handleDelete(job) {
    const message = `Delete "${job.title}" at ${job.company}? Its applications and match results will be deleted too.`;
    if (!window.confirm(message)) return;
    setActionError("");
    try {
      await api.deleteJob(job.id);
      setReloadKey((key) => key + 1);
    } catch (err) {
      setActionError(err.message);
    }
  }

  const jobs = data?.items ?? [];

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">My jobs</h1>
        <button className="btn btn-primary" onClick={() => setShowForm((open) => !open)}>
          {showForm ? "Close form" : "Add job"}
        </button>
      </div>

      {showForm && <JobForm onCreated={handleCreated} />}

      <input
        type="search"
        aria-label="Search jobs"
        placeholder="Search by title, company or location"
        className="field mt-4"
        value={searchInput}
        onChange={(event) => setSearchInput(event.target.value)}
      />

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {!data && loading && <p className="mt-6 text-slate-500">Loading jobs...</p>}

      {data && jobs.length === 0 && !loading && (
        <p className="mt-6 text-slate-500">
          {search
            ? `No jobs match "${search}".`
            : 'No jobs yet. Click "Add job" to save your first one.'}
        </p>
      )}

      <ul className={`mt-4 space-y-3 ${loading ? "opacity-60" : ""}`}>
        {jobs.map((job) => (
          <li key={job.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                                <h2 className="truncate font-medium">
                  <Link to={`/jobs/${job.id}`} className="hover:text-indigo-600 hover:underline">
                    {job.title}
                  </Link>
                </h2>
                <p className="text-sm text-slate-600">
                  {job.company}
                  {job.location ? ` · ${job.location}` : ""}
                </p>
                <p className="mt-1 text-xs text-slate-400">Added {formatDate(job.created_at)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {safeUrl(job.url) && (
                  <a
                    className="btn"
                    href={safeUrl(job.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Posting
                  </a>
                )}
                <button className="btn btn-danger" onClick={() => handleDelete(job)}>
                  Delete
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {data && (
        <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
      )}
    </div>
  );
}