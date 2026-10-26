import { useRef, useState } from "react";
import { api } from "../api.js";
import SkillChips from "../components/SkillChips.jsx";
import { formatDate } from "../format.js";
import { useQuery } from "../hooks.js";

// Loaded only when "View extracted text" is clicked, because this component
// only exists while the text is open.
function ExtractedText({ resumeId }) {
  const { data, error } = useQuery(`resume-${resumeId}`, () => api.getResume(resumeId));

  if (error) return <p className="mt-2 text-sm text-red-700">{error}</p>;
  if (!data) return <p className="mt-2 text-sm text-slate-500">Loading...</p>;
  return (
    <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-xs text-slate-700">
      {data.raw_text}
    </pre>
  );
}

function ResumeCard({ resume, onDeleted, onError }) {
  const [showText, setShowText] = useState(false);

  async function handleDelete() {
    const message = `Delete "${resume.original_filename}"? Its match results will be deleted too.`;
    if (!window.confirm(message)) return;
    try {
      await api.deleteResume(resume.id);
      onDeleted();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate font-medium">{resume.original_filename}</h2>
          <p className="text-xs text-slate-400">
            Uploaded {formatDate(resume.uploaded_at)} ·{" "}
            {Math.max(1, Math.round(resume.size_bytes / 1024))} KB
          </p>
        </div>
        <button className="btn btn-danger" onClick={handleDelete}>
          Delete
        </button>
      </div>

      <p className="mb-1.5 mt-3 text-sm font-medium text-slate-700">
        Skills found ({resume.parsed_skills.length})
      </p>
      <SkillChips skills={resume.parsed_skills} empty="No known skills were found in this resume." />

      <button
        className="mt-3 text-sm font-medium text-indigo-600 hover:underline"
        onClick={() => setShowText((open) => !open)}
      >
        {showText ? "Hide extracted text" : "View extracted text"}
      </button>
      {showText && <ExtractedText resumeId={resume.id} />}
    </li>
  );
}

export default function Resumes() {
  const { data, error, loading, reload } = useQuery("resumes", () => api.listResumes());
  const [uploading, setUploading] = useState(false);
  const [actionError, setActionError] = useState("");
  const fileInput = useRef(null);

  async function handleUpload(event) {
    event.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setActionError("Choose a PDF file first.");
      return;
    }
    setUploading(true);
    setActionError("");
    try {
      await api.uploadResume(file);
      fileInput.current.value = ""; // clear the file picker
      reload();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setUploading(false);
    }
  }

  const resumes = data ?? [];
  const shownError = actionError || error;

  return (
    <div>
      <h1 className="text-2xl font-semibold">My resumes</h1>

      <form
        onSubmit={handleUpload}
        className="mt-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
      >
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf,.pdf"
          aria-label="Resume PDF"
          className="text-sm file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-slate-100"
        />
        <button type="submit" className="btn btn-primary" disabled={uploading}>
          {uploading ? "Uploading..." : "Upload PDF"}
        </button>
      </form>
      <p className="mt-2 text-xs text-slate-500">
        PDF only, up to 5 MB and 10 pages. Scanned or image-only PDFs can not be read.
      </p>

      {shownError && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {shownError}
        </p>
      )}

      {!data && loading && <p className="mt-6 text-slate-500">Loading resumes...</p>}

      {data && resumes.length === 0 && (
        <p className="mt-6 text-slate-500">No resumes yet. Upload one to start matching.</p>
      )}

      <ul className="mt-4 space-y-3">
        {resumes.map((resume) => (
          <ResumeCard key={resume.id} resume={resume} onDeleted={reload} onError={setActionError} />
        ))}
      </ul>
    </div>
  );
}