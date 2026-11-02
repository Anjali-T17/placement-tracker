// Talks to the Flask backend (Phase 2). Replaces mock-data.js and logic.js.
const API_BASE = "/api";

class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

async function request(method, path, body) {
  let res;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError("Cannot reach the backend. Is Flask running on port 5001?", 0);
  }
  let data = null;
  try { data = await res.json(); } catch (e) { /* no JSON body */ }
  if (!res.ok) {
    const details = data && data.details;
    const message = details ? Object.values(details).join(" · ") : (data && data.error) || "Request failed";
    throw new ApiError(message, res.status, details);
  }
  return data;
}

const api = {
  get: (p) => request("GET", p),
  post: (p, b) => request("POST", p, b),
  put: (p, b) => request("PUT", p, b),
  patch: (p, b) => request("PATCH", p, b),
  delete: (p) => request("DELETE", p),
};

// Local copy of server data, so pages can render quickly
const DB = { students: [], jobs: [], applications: [], interviews: [] };

async function loadAll() {
  const [students, jobs, applications, interviews] = await Promise.all([
    api.get("/students"), api.get("/jobs"), api.get("/applications"), api.get("/interviews"),
  ]);
  DB.students = students; DB.jobs = jobs; DB.applications = applications; DB.interviews = interviews;
}

// Re-fetch everything, then redraw the page (each page defines its own render())
async function refresh() { await loadAll(); render(); }

const getStudent = (id) => DB.students.find((s) => s.id === id);
const getJob = (id) => DB.jobs.find((j) => j.id === id);

function apiError(e) {
  console.error(e);
  showToast(e.message || "Something went wrong", "error");
}

// Show server validation messages under the matching form fields.
// map = { serverField: "element-id-of-error-div" }. Returns true if any were shown.
function showFieldErrors(e, map) {
  if (!e.details) return false;
  let shown = false;
  for (const [field, msg] of Object.entries(e.details)) {
    if (map[field] && document.getElementById(map[field])) {
      document.getElementById(map[field]).textContent = msg;
      shown = true;
    }
  }
  return shown;
}

function todayISO() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function checksHtml(res) {
  return res.checks.map((c) => `
    <div class="check-row ${c.ok ? "pass" : "fail"}">
      <span class="check-ico">${c.ok ? "✔" : "✖"}</span>
      <div><div class="cell-main">${esc(c.label)}</div><div class="cell-sub">${esc(c.detail)}</div></div>
    </div>`).join("");
}
