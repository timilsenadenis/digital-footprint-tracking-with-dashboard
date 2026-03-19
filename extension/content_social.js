/**
 * content_social.js — injected into social media pages
 * Detects likes, posts, shares, comments, and scroll depth
 */

(function () {
  const PLATFORM = (() => {
    const h = location.hostname;
    if (h.includes("facebook"))  return "facebook";
    if (h.includes("instagram")) return "instagram";
    if (h.includes("twitter") || h.includes("x.com")) return "twitter";
    if (h.includes("linkedin"))  return "linkedin";
    if (h.includes("tiktok"))    return "tiktok";
    if (h.includes("reddit"))    return "reddit";
    return "unknown";
  })();

  let scrollDepth = 0;
  let pageEnter   = Date.now();

  function send(action, extra = {}) {
    chrome.runtime.sendMessage({
      type:          "SOCIAL_EVENT",
      platform:      PLATFORM,
      action,
      time_spent_sec: Math.round((Date.now() - pageEnter) / 1000),
      ...extra,
    });
  }

  // ── Scroll tracking ──────────────────────────────────
  let lastScroll = 0;
  window.addEventListener("scroll", () => {
    const depth = Math.round(
      (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
    );
    if (depth > scrollDepth + 20) {
      scrollDepth = depth;
      send("scroll", { content_type: "feed" });
    }
  }, { passive: true });

  // ── Click-based action detection ─────────────────────
  const ACTION_SELECTORS = {
    facebook: {
      like:    '[aria-label*="Like"]',
      share:   '[aria-label*="Share"]',
      comment: '[aria-label*="Comment"]',
    },
    twitter: {
      like:    '[data-testid="like"]',
      share:   '[data-testid="retweet"]',
      comment: '[data-testid="reply"]',
    },
    instagram: {
      like:    '[aria-label*="Like"]',
      comment: '[aria-label*="Comment"]',
    },
    linkedin: {
      like:    '[aria-label*="React"]',
      share:   '[aria-label*="Share"]',
      comment: '[aria-label*="Comment"]',
    },
    reddit: {
      like:    '[aria-label*="upvote"]',
      comment: '[data-click-id="comments"]',
      share:   '[data-click-id="share"]',
    },
  };

  const selectors = ACTION_SELECTORS[PLATFORM] || {};
  document.addEventListener("click", (e) => {
    for (const [action, sel] of Object.entries(selectors)) {
      if (e.target.closest(sel)) {
        send(action);
        break;
      }
    }
  }, true);

  // ── Flush on page unload ──────────────────────────────
  window.addEventListener("beforeunload", () => {
    send("page_leave");
  });
})();
