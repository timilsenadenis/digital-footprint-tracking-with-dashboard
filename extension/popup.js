const API = "http://localhost:5000/api";

// ── Helpers ───────────────────────────────────────────
async function getToken() {
  const d = await chrome.storage.local.get("token");
  return d.token || null;
}

function fmtTime(sec) {
  if (!sec || sec <= 0) return "0m";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  return h ? `${h}h ${m}m` : `${m}m`;
}

function showLogin() {
  document.getElementById("login-view").style.display  = "block";
  document.getElementById("status-view").style.display = "none";
  document.getElementById("dot").classList.remove("green");
}

function showStatus() {
  document.getElementById("login-view").style.display  = "none";
  document.getElementById("status-view").style.display = "block";
  document.getElementById("dot").classList.add("green");
}

// ── Load today's stats ────────────────────────────────
async function loadStats(token) {
  try {
    const res  = await fetch(`${API}/analytics/summary?days=1`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const rows = await res.json();
    if (Array.isArray(rows) && rows.length > 0) {
      const r = rows[rows.length - 1];
      document.getElementById("s-visits").textContent  = r.total_visits   || 0;
      document.getElementById("s-time").textContent    = fmtTime(r.total_time_sec);
      document.getElementById("s-social").textContent  = r.social_visits  || 0;
      document.getElementById("s-domains").textContent = r.unique_domains || 0;
    }
  } catch (e) {
    console.log("Stats error:", e);
  }

  // Show current tab URL
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url && !tab.url.startsWith("chrome://")) {
      const hostname = new URL(tab.url).hostname.replace("www.", "");
      document.getElementById("s-url").textContent = "Now: " + hostname;
    }
  } catch {}
}

// ── Init ──────────────────────────────────────────────
async function init() {
  const token = await getToken();
  if (token) {
    showStatus();
    loadStats(token);
  } else {
    showLogin();
  }
}

// ── Login button ──────────────────────────────────────
document.getElementById("login-btn").addEventListener("click", async () => {
  const email    = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errEl    = document.getElementById("err");

  if (!email || !password) {
    errEl.textContent = "Please enter email and password";
    return;
  }

  errEl.textContent = "Signing in...";

  try {
    const res = await fetch(`${API}/login`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ email, password }),
    });
    const data = await res.json();

    if (data.token) {
      await chrome.storage.local.set({ token: data.token });
      errEl.textContent = "";
      showStatus();
      loadStats(data.token);
    } else {
      errEl.textContent = data.error || "Login failed. Check credentials.";
    }
  } catch (e) {
    errEl.textContent = "Cannot connect to localhost:5000 — is Flask running?";
  }
});

// ── Dashboard button ──────────────────────────────────
document.getElementById("dash-btn").addEventListener("click", () => {
  chrome.tabs.create({ url: "http://localhost:5000" });
});

// ── Logout button ─────────────────────────────────────
document.getElementById("logout-btn").addEventListener("click", async () => {
  await chrome.storage.local.remove("token");
  showLogin();
});

// ── Start ─────────────────────────────────────────────
init();
