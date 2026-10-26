import { useState } from "react";
import { Link } from "react-router";
import { api } from "../api.js";
import { formatDate } from "../format.js";
import { useQuery } from "../hooks.js";
import SkillChips from "./SkillChips.jsx";

function barColor(score) {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function ScoreBar({ value }) {
  const width = Math.min(100, Math.max(0, value));
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-slate-100"
      role="img"
      aria-label={`Score ${Math.round(value)} out of 100`}
    >
      <div className={`h-full rounded-full ${barColor(value)}`} style={{ width: `${width}%` }} />
    </div>
  );
}

function MatchCard({ match, resumeName, isBest }) {
  const skillText =
    match.skill_score === null ? "not available" : `${Math.round(match.skill_score)}%`;

  return (
    <li className="rounded-lg border border-slate-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{resumeName ?? `Resume #${match.resume_id}`}</p>
          {isBest && (
            <span className="mt-1 inline-block rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              Best match
            </span>
          )}
        </div>
        <p className="text-2xl font-semibold">{Math.round(match.score)}%</p>
      </div>

      <div className="mt-2">
        <ScoreBar value={match.score} />
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Skills: {skillText} · Wording: {Math.round(match.text_score)}% · Updated{" "}
        {formatDate(match.computed_at)}
      </p>
      {match.skill_score === null && (
        <p className="mt-1 text-xs text-slate-500">
          None of the skills we recognise were found in this job, so only the wording was compared.
        </p>
      )}

      <p className="mb-1.5 mt-4 text-sm font-medium text-slate-700">Skills you have that it asks for</p>
      <SkillChips skills={match.matched_skills} tone="good" empty="None of its skills found in this resume." />

      <p className="mb-1.5 mt-4 text-sm font-medium text-slate-700">Skills it asks for that you are missing</p>
      <SkillChips skills={match.missing_skills} tone="bad" empty="Nothing missing. You cover every skill it lists." />
    </li>
  );
}

export default function MatchPanel({ job }) {
  const resumesQuery = useQuery("resumes", () => api.listResumes());
  const matchesQuery = useQuery(`matches-${job.id}`, () => api.listMatches({ jobId: job.id }));
  const [selected, setSelected] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const resumes = resumesQuery.data ?? [];
  const matches = matchesQuery.data ?? [];
  const resumeNames = Object.fromEntries(resumes.map((resume) => [resume.id, resume.original_filename]));
  // Until the user picks one, the first resume is selected
  const resumeId = selected || String(resumes[0]?.id ?? "");

  async function handleRun() {
    setRunning(true);
    setError("");
    try {
      await api.runMatch(Number(resumeId), job.id);
      matchesQuery.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  const loadError = resumesQuery.error || matchesQuery.error;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-medium">Resume match</h2>

      {!resumesQuery.data && resumesQuery.loading && (
        <p className="mt-3 text-sm text-slate-500">Loading...</p>
      )}

      {resumesQuery.data && resumes.length === 0 && (
        <p className="mt-3 text-sm text-slate-600">
          You have no resumes yet.{" "}
          <Link to="/resumes" className="font-medium text-indigo-600 hover:underline">
            Upload one
          </Link>{" "}
          to see how well you match this job.
        </p>
      )}

      {resumes.length > 0 && (
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="min-w-0 flex-1">
            <label htmlFor="match-resume" className="mb-1 block text-sm font-medium text-slate-700">
              Resume
            </label>
            <select
              id="match-resume"
              className="field"
              value={resumeId}
              onChange={(event) => setSelected(event.target.value)}
            >
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.original_filename}
                </option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleRun} disabled={running || !resumeId}>
            {running ? "Matching..." : matches.length > 0 ? "Match again" : "Run match"}
          </button>
        </div>
      )}

      {(error || loadError) && (
        <p role="alert" className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error || loadError}
        </p>
      )}

      {matches.length > 0 && (
        <ul className="mt-4 space-y-3">
          {matches.map((match, index) => (
            <MatchCard
              key={match.id}
              match={match}
              resumeName={resumeNames[match.resume_id]}
              isBest={index === 0 && matches.length > 1}
            />
          ))}
        </ul>
      )}
    </section>
  );
}