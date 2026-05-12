// djiang.xyz analytics client. Cookieless. Stores a random visitor id in localStorage.
// Exposes window.track(type, data) for custom events.
(function () {
  // In production, Caddy proxies /api/analytics/* to localhost:8001.
  // On localhost, hit the FastAPI server directly (CORS is allow-listed for :4747).
  var _isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  var ENDPOINT = window.__ANALYTICS_ENDPOINT__
    || (_isLocal ? "http://localhost:8001/event" : "/api/analytics/event");

  // Visitor id (persists across visits; cleared if user clears storage)
  var sid;
  try {
    sid = localStorage.getItem("djv_sid");
    if (!sid) {
      sid = (window.crypto && crypto.randomUUID) ? crypto.randomUUID()
        : "v" + Date.now().toString(36) + Math.random().toString(36).slice(2);
      localStorage.setItem("djv_sid", sid);
    }
  } catch (_e) {
    // localStorage blocked (e.g. some private modes); fall back to a per-pageload id
    sid = "ephemeral-" + Math.random().toString(36).slice(2);
  }

  function send(type, extra) {
    var payload = { type: type, sid: sid, page: location.pathname + location.search, ref: document.referrer || "", ts: Date.now() };
    if (extra) { for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) payload[k] = extra[k]; }
    var body = JSON.stringify(payload);
    try {
      if (navigator.sendBeacon) {
        // sendBeacon needs a Blob to set content-type
        navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
      } else {
        fetch(ENDPOINT, {
          method: "POST",
          body: body,
          headers: { "Content-Type": "application/json" },
          keepalive: true,
          mode: "cors",
        }).catch(function () {});
      }
    } catch (_e) { /* analytics never breaks the page */ }
  }

  // 1) Pageview on load
  send("pageview");

  // 2) Scroll depth — track max % scrolled
  var maxScroll = 0;
  function updateScroll() {
    var docH = document.documentElement.scrollHeight - window.innerHeight;
    if (docH <= 0) return;
    var pct = Math.round((window.scrollY / docH) * 100);
    if (pct > maxScroll) maxScroll = pct;
  }
  window.addEventListener("scroll", updateScroll, { passive: true });
  updateScroll();

  // 3) Duration — sent on tab hide / page unload (whichever fires first)
  var start = Date.now();
  var durationSent = false;
  function flushDuration() {
    if (durationSent) return;
    durationSent = true;
    send("duration", { ms: Date.now() - start, scroll: maxScroll });
  }
  document.addEventListener("visibilitychange", function () { if (document.hidden) flushDuration(); });
  window.addEventListener("pagehide", flushDuration);
  // If user comes back to the tab after hiding, restart the timer
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden && durationSent) { start = Date.now(); durationSent = false; }
  });

  // Expose for custom event tracking
  window.track = send;
})();
