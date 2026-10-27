const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const TOKEN_KEY = "jobtrackr_token";

// ---------- Token storage ----------
// localStorage can be unavailable (private mode, blocked storage), so never trust it blindly.

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore: the user will simply have to log in again next time */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

// ---------- Errors ----------

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// FastAPI sends errors in two shapes: {"detail": "text"} or, for validation
// failures (422), {"detail": [{"loc": [...], "msg": "..."}, ...]}
function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const message = String(item.msg).replace(/^Value error, /, "");
        const field = item.loc?.slice(1).join(".");
        return field ? `${field}: ${message}` : message;
      })
      .join(". ");
  }
  return `Request failed (${status})`;
}

// The auth code registers a function here that logs the user out.
let onUnauthorized = null;
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

// ---------- The one function that talks to the server ----------

async function request(path, { method = "GET", body, form, formData, auth = true } = {}) {
  const headers = {};
  let payload;

  if (formData) {
    // A file upload. Do NOT set Content-Type here: the browser sets it itself,
    // including the boundary that separates the parts of the upload.
    payload = formData;
  } else if (form) {
    // The login endpoint expects form fields, not JSON
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  }

  if (response.status === 204) return null; // success with no body (e.g. DELETE)

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* the response had no JSON body */
  }

  if (!response.ok) {
    // An expired or invalid token on a normal request means: log the user out.
    // Login and register pass auth: false, so a wrong password doesn't trigger this.
    if (response.status === 401 && auth && token && onUnauthorized) onUnauthorized();
    throw new ApiError(response.status, errorMessage(data, response.status));
  }
  return data;
}

// ---------- The API, one function per endpoint ----------

export const api = {
  // Auth
  register: (email, password) =>
    request("/auth/register", { method: "POST", body: { email, password }, auth: false }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", form: { username: email, password }, auth: false }),
  me: () => request("/auth/me"),

  // Jobs
  listJobs: ({ search = "", page = 1, pageSize = 10 } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (search.trim()) params.set("search", search.trim());
    return request(`/jobs?${params}`);
  },
  getJob: (id) => request(`/jobs/${id}`),
  createJob: (job) => request("/jobs", { method: "POST", body: job }),
  deleteJob: (id) => request(`/jobs/${id}`, { method: "DELETE" }),

  // Applications
  listApplications: ({ status, page = 1, pageSize = 100 } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (status) params.set("status", status);
    return request(`/applications?${params}`);
  },
  trackJob: (jobId) => request("/applications", { method: "POST", body: { job_id: jobId } }),
  changeStatus: (id, status) =>
    request(`/applications/${id}/status`, { method: "PATCH", body: { status } }),
  applicationHistory: (id) => request(`/applications/${id}/history`),
  deleteApplication: (id) => request(`/applications/${id}`, { method: "DELETE" }),

  // Resumes
  listResumes: () => request("/resumes"),
  getResume: (id) => request(`/resumes/${id}`),
  uploadResume: (file) => {
    const formData = new FormData();
    formData.append("file", file); // "file" is the field name the backend expects
    return request("/resumes", { method: "POST", formData });
  },
  deleteResume: (id) => request(`/resumes/${id}`, { method: "DELETE" }),

  // Matching
  runMatch: (resumeId, jobId) =>
    request("/match", { method: "POST", body: { resume_id: resumeId, job_id: jobId } }),
  listMatches: ({ jobId, resumeId } = {}) => {
    const params = new URLSearchParams();
    if (jobId) params.set("job_id", jobId);
    if (resumeId) params.set("resume_id", resumeId);
    const query = params.toString();
    return request(`/match${query ? `?${query}` : ""}`);
  },

  // Analytics
  funnel: () => request("/analytics/funnel"),
  weekly: (weeks = 12) => request(`/analytics/weekly?weeks=${weeks}`),
  weakSpots: (limit = 10) => request(`/analytics/weak-spots?limit=${limit}`),
    // Reminders
  listReminders: ({ status, applicationId } = {}) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (applicationId) params.set("application_id", applicationId);
    const query = params.toString();
    return request(`/reminders${query ? `?${query}` : ""}`);
  },
  createReminder: (applicationId, remindAt, note) =>
    request(`/applications/${applicationId}/reminders`, {
      method: "POST",
      body: { remind_at: remindAt, note: note || null },
    }),
  deleteReminder: (id) => request(`/reminders/${id}`, { method: "DELETE" }),
};