import { useState } from "react";
import { api } from "../api.js";

const EMPTY = { title: "", company: "", location: "", url: "", description: "" };

function Field({ label, name, ...props }) {
  return (
    <div>
      <label htmlFor={name} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input id={name} name={name} className="field" {...props} />
    </div>
  );
}

export default function JobForm({ onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.createJob({
        title: form.title.trim(),
        company: form.company.trim(),
        // The API expects null for "not provided", not an empty string
        location: form.location.trim() || null,
        url: form.url.trim() || null,
        description: form.description.trim(),
      });
      setForm(EMPTY);
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-4 space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Job title" name="title" required maxLength={255} value={form.title} onChange={handleChange} />
        <Field label="Company" name="company" required maxLength={255} value={form.company} onChange={handleChange} />
        <Field label="Location" name="location" maxLength={255} value={form.location} onChange={handleChange} />
        <Field
          label="Posting URL"
          name="url"
          type="url"
          placeholder="https://..."
          maxLength={500}
          value={form.url}
          onChange={handleChange}
        />
      </div>

      <div>
        <label htmlFor="description" className="mb-1 block text-sm font-medium text-slate-700">
          Job description
        </label>
        <textarea
          id="description"
          name="description"
          required
          rows={6}
          maxLength={20000}
          className="field"
          placeholder="Paste the full job description here. The resume matcher reads it."
          value={form.description}
          onChange={handleChange}
        />
      </div>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <button type="submit" disabled={submitting} className="btn btn-primary">
        {submitting ? "Saving..." : "Save job"}
      </button>
    </form>
  );
}