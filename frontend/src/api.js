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

async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  let payload;

  if (form) {
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
  register: (email, password) =>
    request("/auth/register", { method: "POST", body: { email, password }, auth: false }),

  login: (email, password) =>
    request("/auth/login", { method: "POST", form: { username: email, password }, auth: false }),

  me: () => request("/auth/me"),

  listJobs: ({ search = "", page = 1, pageSize = 10 } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (search.trim()) params.set("search", search.trim());
    return request(`/jobs?${params}`);
  },

  createJob: (job) => request("/jobs", { method: "POST", body: job }),

  deleteJob: (id) => request(`/jobs/${id}`, { method: "DELETE" }),
};