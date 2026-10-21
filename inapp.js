/* Open pickshelf (and the partner links on it) in the phone's real browser when it was opened inside
   an app's in-app browser (Instagram, Threads, Facebook, KakaoTalk ...). Shopping/booking apps and
   saved logins only work in the real browser.
   - Android: hand the URL to the phone's default browser with an intent:// link (no app pinned).
   - KakaoTalk: its own "open externally" scheme.
   - iOS: apps give pages no way to leave on their own, so show a short how-to banner
     (plus a Safari button that works on newer iOS versions). */
(function () {
  var ua = navigator.userAgent || "";
  var inApp = /Instagram|Barcelona|Threads|FBAN|FBAV|FB_IAB|FBIOS|KAKAOTALK|NAVER\(inapp|Line\/|DaumApps|everytimeApp/i.test(ua);
  if (!inApp) return;
  var android = /Android/i.test(ua), ios = /iPhone|iPad|iPod/i.test(ua), kakao = /KAKAOTALK/i.test(ua);

  function external(url) {
    if (kakao) return "kakaotalk://web/openExternal?url=" + encodeURIComponent(url);
    if (android) {
      var u = new URL(url);
      return "intent://" + u.host + u.pathname + u.search + u.hash +
        "#Intent;scheme=" + u.protocol.replace(":", "") + ";action=android.intent.action.VIEW;category=android.intent.category.BROWSABLE;S.browser_fallback_url=" +
        encodeURIComponent(url) + ";end";
    }
    if (ios) return "x-safari-" + url;  // iOS 17+; older versions ignore it and the banner explains the menu
    return url;
  }

  // Android / KakaoTalk: move the whole page out once (the flag stops a loop if no browser takes it).
  try {
    if ((android || kakao) && !sessionStorage.getItem("ps_ext")) {
      sessionStorage.setItem("ps_ext", "1");
      location.href = external(location.href);
    }
  } catch (e) {}

  // Partner links opened from inside the in-app browser also go out to the real browser.
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest('a[rel~="sponsored"]');
    if (!a || !(android || kakao)) return;
    ev.preventDefault();
    location.href = external(a.href);
  }, true);

  if (!ios) return;
  var css = ".ps-ext{position:sticky;top:0;z-index:9;margin:-20px -16px 12px;padding:10px 14px;background:#1c1b17;color:#fff;font-size:13px;line-height:1.45;display:flex;gap:10px;align-items:center}" +
    ".ps-ext b{color:#ffd400}.ps-ext a{flex:0 0 auto;background:#ffd400;color:#1c1b17;font-weight:700;border-radius:8px;padding:6px 10px;text-decoration:none}" +
    ".ps-ext button{flex:0 0 auto;background:none;border:0;color:#aaa;font-size:18px;padding:0 2px}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);
  var bar = document.createElement("div"); bar.className = "ps-ext";
  bar.innerHTML = '<span>앱 안에서 열렸어요. 오른쪽 위 <b>⋯</b> → <b>외부 브라우저로 열기</b>를 누르면 쇼핑·예약 앱으로 바로 연결돼요.</span>' +
    '<a href="' + external(location.href) + '">Safari</a><button aria-label="닫기">×</button>';
  bar.querySelector("button").onclick = function () { bar.remove(); };
  var wrap = document.querySelector(".wrap") || document.body;
  wrap.insertBefore(bar, wrap.firstChild);
})();
