/* Visitor stats with Google Analytics 4: visitors, page views, where visitors came from, which links
   they tap and what they search for. Reports: analytics.google.com
   - Page views / visitors / traffic source: GA4 records these on its own.
   - link_click: every link tap, with the partner (coupang/agoda/trip ...), item number and name.
   - search: what was typed into the search box (sent once typing pauses).
   Set GA_ID to the site's Measurement ID (GA4 → Admin → Data streams → G-XXXXXXXXXX). */
(function () {
  var GA_ID = "G-XXXXXXXXXX";
  if (GA_ID === "G-XXXXXXXXXX") return;  // not set up yet

  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;

  function start() {
    var s = document.createElement("script");
    s.async = true; s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
    gtag("js", new Date());
    gtag("config", GA_ID);
  }
  // inapp.js may be moving this page out to the real browser, where it is counted again.
  // Count the in-app visit only if the page is still showing a moment later (the move failed).
  if (window.psLeaving) setTimeout(function () { if (document.visibilityState === "visible") start(); }, 3000);
  else start();

  function partner(host) {
    var m = host.match(/(coupang|agoda|trip|booking|expedia|hotels|airbnb|naver|youtube|instagram|threads)\./);
    return m ? m[1] : host.replace(/^www\./, "");
  }

  // Capture phase so the event is queued before inapp.js hands partner links to an app.
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("a[href]");
    if (!a) return;
    var u = new URL(a.href, location.href), card = a.closest(".card"), name = card && card.querySelector(".name");
    var external = u.host !== location.host;
    gtag("event", "link_click", {
      link_type: /\bsponsored\b/.test(a.rel) ? "partner" : external ? "outbound" : "internal",
      partner: external ? partner(u.host) : "",
      item_no: card ? card.dataset.no || "" : "",
      item_name: name ? name.textContent.trim().slice(0, 100) : a.textContent.trim().slice(0, 100),
      button: a.className || "",
      link_url: u.href.slice(0, 300),
      transport_type: "beacon"
    });
  }, true);

  var q = document.getElementById("q"), timer, last = "";
  if (q) q.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var v = q.value.trim();
      if (v && v !== last) { last = v; gtag("event", "search", { search_term: v.slice(0, 100) }); }
    }, 1500);
  });
})();
