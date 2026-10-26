export default function Pagination({ page, pages, total, onChange }) {
  if (pages <= 1) return null;

  return (
    <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pagination">
      <span className="text-slate-500">
        Page {page} of {pages} · {total} jobs
      </span>
      <div className="flex gap-2">
        <button className="btn" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </button>
        <button className="btn" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  );
}