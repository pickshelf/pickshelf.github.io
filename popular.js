/* "🔥 N명이 봤어요" on cards that many people opened recently, so visitors see what others look at.
   Numbers come from /popular.json, which scripts/popular.py rebuilds daily from GA
   (people who tapped the card's partner link in the last 30 days; small counts are left out there).
   The mark goes first in the card's .pts row, matching the other chips. */
(function () {
  var page = location.pathname.replace(/index\.html$/, "");
  if (!/\/$/.test(page)) page += "/";

  fetch("/popular.json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (all) {
    var items = all[page];
    if (!items) return;
    var css = document.createElement("style");
    css.textContent = ".pts li.hot{color:#e8492f;border-color:color-mix(in srgb,#e8492f 40%,transparent);font-weight:700}";
    document.head.appendChild(css);
    Object.keys(items).forEach(function (no) {
      var card = document.querySelector('.card[data-no="' + no + '"]'), pts = card && card.querySelector(".pts");
      if (!pts) return;
      var li = document.createElement("li");
      li.className = "hot";
      li.textContent = "🔥 " + items[no] + "명이 봤어요";
      pts.insertBefore(li, pts.firstChild);
    });
  }).catch(function () {});
})();
