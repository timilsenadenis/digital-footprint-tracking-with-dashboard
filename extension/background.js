/**
 * Digital Footprint Tracker — Background Service Worker
 * Tracks: URL visits, time-on-site, search queries, app/tab usage
 */

const API_BASE = "http://localhost:5000/api";

// ─────────────────────────────────────────
//  State (in-memory per service worker)
// ─────────────────────────────────────────
let activeTab = {
  tabId:    null,
  url:      null,
  title:    null,
  start_ts: null,
};

const SEARCH_ENGINES = {
  "google.com":     { param: "q",      name: "google"     },
  "bing.com":       { param: "q",      name: "bing"       },
  "duckduckgo.com": { param: "q",      name: "duckduckgo" },
  "yahoo.com":      { param: "p",      name: "yahoo"      },
  "baidu.com":      { param: "wd",     name: "baidu"      },
};

const SOCIAL_PLATFORMS = [
  "facebook.com", "instagram.com", "twitter.com", "x.com",
  "linkedin.com", "tiktok.com", "reddit.com",
];

// ─────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────
async function getToken() {
  const data = await chrome.storage.local.get("token");
  return data.token || null;
}

async function post(endpoint, body) {
  const token = await getToken();
  if (!token) return;
  try {
    await fetch(`${API_BASE}${endpoint}`, {
      method:  "POST",
      headers: {
        "Content-Type":  "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
  } catch (err) {
    console.warn("[Footprint] POST failed:", err);
  }
}

function extractDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function extractSearchQuery(url) {
  const domain = extractDomain(url);
  if (!domain) return null;
  for (const [key, engine] of Object.entries(SEARCH_ENGINES)) {
    if (domain.includes(key)) {
      const params = new URL(url).searchParams;
      const query  = params.get(engine.param);
      if (query) return { query, engine: engine.name };
    }
  }
  return null;
}

function isSocialMedia(url) {
  const domain = extractDomain(url);
  return domain ? SOCIAL_PLATFORMS.some(p => domain.includes(p)) : false;
}

function getPlatform(url) {
  const domain = extractDomain(url);
  return SOCIAL_PLATFORMS.find(p => domain?.includes(p)) || null;
}

// ─────────────────────────────────────────
//  Flush active tab visit to API
// ─────────────────────────────────────────
async function flushVisit() {
  if (!activeTab.url || !activeTab.start_ts) return;
  const end_ts = Date.now() / 1000;
  const duration = end_ts - activeTab.start_ts;
  if (duration < 2) return; // ignore blink-through tabs

  await post("/track/visit", {
    url:       activeTab.url,
    title:     activeTab.title,
    start_ts:  activeTab.start_ts,
    end_ts:    end_ts,
    browser:   "chrome",
    incognito: false,
  });

  // Check if this was a search
  const search = extractSearchQuery(activeTab.url);
  if (search) {
    await post("/track/search", {
      query:     search.query,
      engine:    search.engine,
      timestamp: activeTab.start_ts,
    });
  }

  // Social media visit
  if (isSocialMedia(activeTab.url)) {
    await post("/track/social", {
      platform:      getPlatform(activeTab.url),
      action:        "visit",
      time_spent_sec: Math.round(duration),
      timestamp:     activeTab.start_ts,
    });
  }

  activeTab = { tabId: null, url: null, title: null, start_ts: null };
}

// ─────────────────────────────────────────
//  Tab event listeners
// ─────────────────────────────────────────
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  await flushVisit();
  const tab = await chrome.tabs.get(tabId);
  if (!tab.url || tab.url.startsWith("chrome://")) return;
  activeTab = {
    tabId,
    url:      tab.url,
    title:    tab.title,
    start_ts: Date.now() / 1000,
  };
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== "complete") return;
  if (!tab.url || tab.url.startsWith("chrome://")) return;
  if (tabId === activeTab.tabId && tab.url !== activeTab.url) {
    await flushVisit();
  }
  if (tabId === activeTab.tabId || activeTab.tabId === null) {
    activeTab = {
      tabId,
      url:      tab.url,
      title:    tab.title,
      start_ts: Date.now() / 1000,
    };
  }
});

chrome.tabs.onRemoved.addListener(async (tabId) => {
  if (tabId === activeTab.tabId) {
    await flushVisit();
  }
});

chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) {
    await flushVisit();
  }
});

// ─────────────────────────────────────────
//  Periodic flush alarm (every 2 minutes)
// ─────────────────────────────────────────
chrome.alarms.create("periodic-flush", { periodInMinutes: 2 });
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "periodic-flush") {
    // Update visit_end without clearing (still ongoing)
    if (activeTab.url && activeTab.start_ts) {
      const now = Date.now() / 1000;
      await post("/track/visit", {
        url:       activeTab.url,
        title:     activeTab.title,
        start_ts:  activeTab.start_ts,
        end_ts:    now,
        browser:   "chrome",
        incognito: false,
      });
    }
  }
});

// ─────────────────────────────────────────
//  Message listener (from popup / content scripts)
// ─────────────────────────────────────────
chrome.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg.type === "SOCIAL_EVENT") {
    await post("/track/social", {
      platform:      msg.platform,
      action:        msg.action,
      content_type:  msg.content_type || null,
      time_spent_sec: msg.time_spent_sec || 0,
      timestamp:     Date.now() / 1000,
    });
  }
  if (msg.type === "APP_USAGE") {
    await post("/track/app", msg.data);
  }
  if (msg.type === "GET_STATUS") {
    return { active: !!activeTab.url, url: activeTab.url };
  }
});
