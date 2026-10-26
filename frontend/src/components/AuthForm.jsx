import { useState } from "react";

export default function AuthForm({ title, submitLabel, onSubmit, footer, isNewAccount = false }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault(); // stop the browser from reloading the page
    setError("");
    setSubmitting(true);
    try {
      await onSubmit(email.trim(), password);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              className="field"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={isNewAccount ? 8 : undefined}
              autoComplete={isNewAccount ? "new-password" : "current-password"}
              className="field"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {isNewAccount && <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p>}
          </div>

          {error && (
            <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button type="submit" disabled={submitting} className="btn btn-primary w-full">
            {submitting ? "Please wait..." : submitLabel}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-600">{footer}</p>
      </div>
    </div>
  );
}