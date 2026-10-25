/* "👀 N명이 봤어요" on cards that many people opened recently, so visitors see what others look at.
   Numbers come from /popular.json, which scripts/popular.py rebuilds daily from GA
   (people who tapped the card's partner link in the last 30 days; small counts are left out there).
   The mark is a bar across the bottom of the card photo; the tier badge moves up above it. */
(function () {
  var page = location.pathname.replace(/index\.html$/, "");
  if (!/\/$/.test(page)) page += "/";

  fetch("/popular.json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (all) {
    var items = all[page];
    if (!items) return;
    var css = document.createElement("style");
    // Site yellow, so it doesn't read as the red Agoda / blue Trip.com buttons or the tier badges.
    css.textContent = ".thumb .hot{position:absolute;left:0;right:0;bottom:0;background:#ffd400;color:#1c1b17;" +
      "font-size:10.5px;font-weight:700;text-align:center;white-space:nowrap;padding:2px 0}" +
      ".card .thumb.has-hot .tier{bottom:24px}";
    document.head.appendChild(css);
    Object.keys(items).forEach(function (no) {
      var card = document.querySelector('.card[data-no="' + no + '"]'), thumb = card && card.querySelector(".thumb");
      if (!thumb) return;
      var bar = document.createElement("span");
      bar.className = "hot";
      bar.textContent = "👀 " + items[no] + "명이 봤어요";
      thumb.appendChild(bar);
      thumb.classList.add("has-hot");
    });
  }).catch(function () {});
})();
