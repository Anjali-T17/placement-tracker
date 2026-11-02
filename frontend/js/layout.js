// Shared layout: sidebar + topbar + toast + helpers
const NAV_ITEMS = [
  { id: "dashboard",    label: "Dashboard",           icon: "📊", href: "index.html" },
  { id: "students",     label: "Student Management",  icon: "🎓", href: "students.html" },
  { id: "jobs",         label: "Job Listings",        icon: "💼", href: "jobs.html" },
  { id: "applications", label: "Applications",        icon: "📝", href: "applications.html" },
  { id: "eligibility",  label: "Eligibility Check",   icon: "✅", href: "eligibility.html" },
  { id: "interviews",   label: "Interview Schedule",  icon: "📅", href: "interviews.html" },
  { id: "status",       label: "Status Tracking",     icon: "🔍", href: "status.html" },
];

function renderLayout(pageId, title, subtitle) {
  const links = NAV_ITEMS.map(
    (n) => `<a href="${n.href}" class="${n.id === pageId ? "active" : ""}">
              <span class="ico">${n.icon}</span>${n.label}</a>`
  ).join("");

  document.getElementById("sidebar").outerHTML = `
    <aside class="sidebar" id="sidebar">
      <div class="brand"><div class="brand-logo">🎯</div>PlacementTracker</div>
      <nav class="nav">
        <div class="nav-label">Menu</div>
        ${links}
      </nav>
      <div class="sidebar-footer">College Placement Cell<br>© 2026</div>
    </aside>`;

  document.getElementById("topbar").outerHTML = `
    <header class="topbar">
      <div class="topbar-left">
        <button class="menu-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
        <div><h1>${title}</h1><div class="sub">${subtitle}</div></div>
      </div>
      <div class="topbar-right">
        <span class="sub">Admin</span>
        <div class="avatar">A</div>
      </div>
    </header>`;

  const t = document.createElement("div");
  t.id = "toast-container";
  document.body.appendChild(t);
}

function showToast(message, type = "success") {
  const el = document.createElement("div");
  el.className = "toast " + (type === "error" ? "error" : "");
  el.textContent = message;
  document.getElementById("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function openModal(id)  { document.getElementById(id).classList.add("show"); }
function closeModal(id) { document.getElementById(id).classList.remove("show"); }

function statusBadge(status) {
  const map = {
    "Applied": "applied",
    "Shortlisted": "shortlisted",
    "Interview Scheduled": "interview",
    "Selected": "selected",
    "Rejected": "rejected",
    "Open": "open",
    "Closed": "closed",
  };
  return `<span class="badge badge-${map[status] || "applied"}">${status}</span>`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

// Escapes text so user input can never inject HTML (prevents XSS)
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
