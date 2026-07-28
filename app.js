/* KoreanFreedomFighters — progressive enhancements.
   Everything here is additive: the pages are fully readable with JS disabled. */
(function () {
  "use strict";

  var doc = document;
  var mq = window.matchMedia("(max-width: 960px)");

  /* ---------------------------------------------------------- sticky header */
  var masthead = doc.querySelector(".masthead");
  if (masthead) {
    var onScroll = function () {
      masthead.dataset.stuck = window.scrollY > 8 ? "true" : "false";
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ------------------------------------------------------------ dropdown nav */
  var items = Array.prototype.slice.call(doc.querySelectorAll(".nav__item"));

  function close(item) {
    item.dataset.open = "false";
    delete item.dataset.via;
    var t = item.querySelector(".nav__toggle");
    if (t) t.setAttribute("aria-expanded", "false");
  }

  function open(item, via) {
    items.forEach(function (other) { if (other !== item) close(other); });
    item.dataset.open = "true";
    item.dataset.via = via || "click";
    var t = item.querySelector(".nav__toggle");
    if (t) t.setAttribute("aria-expanded", "true");
  }

  items.forEach(function (item) {
    var toggle = item.querySelector(".nav__toggle");
    if (!toggle) return;

    close(item);

    toggle.addEventListener("click", function () {
      /* if hover already opened it, the click pins it open instead of closing */
      if (item.dataset.open === "true" && item.dataset.via === "hover") {
        item.dataset.via = "click";
      } else if (item.dataset.open === "true") {
        close(item);
      } else {
        open(item, "click");
      }
    });

    /* hover only makes sense on pointer devices with room for the flyout */
    item.addEventListener("mouseenter", function () {
      if (!mq.matches && window.matchMedia("(hover: hover)").matches) open(item, "hover");
    });
    item.addEventListener("mouseleave", function () {
      if (!mq.matches && window.matchMedia("(hover: hover)").matches) close(item);
    });

    /* keyboard: focus leaving the group closes it */
    item.addEventListener("focusout", function (e) {
      if (!item.contains(e.relatedTarget)) close(item);
    });
  });

  doc.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    var openItem = items.filter(function (i) { return i.dataset.open === "true"; })[0];
    if (openItem) {
      var t = openItem.querySelector(".nav__toggle");
      close(openItem);
      if (t) t.focus();
    } else if (doc.body.dataset.menu === "open") {
      setMenu(false);
      var b = doc.querySelector(".burger");
      if (b) b.focus();
    }
  });

  doc.addEventListener("click", function (e) {
    if (e.target.closest(".nav__item")) return;
    items.forEach(close);
  });

  /* ------------------------------------------------------------ mobile menu */
  var burger = doc.querySelector(".burger");

  function setMenu(isOpen) {
    doc.body.dataset.menu = isOpen ? "open" : "closed";
    if (burger) burger.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (!isOpen) items.forEach(close);
  }

  if (burger) {
    setMenu(false);
    burger.addEventListener("click", function () {
      setMenu(doc.body.dataset.menu !== "open");
    });
  }

  /* a tap on a real link should always leave the drawer closed */
  doc.querySelectorAll(".nav a").forEach(function (a) {
    a.addEventListener("click", function () { setMenu(false); });
  });

  mq.addEventListener("change", function (e) { if (!e.matches) setMenu(false); });

  /* --------------------------------------------------------- scroll reveals */
  var reveals = doc.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.dataset.seen = "true";
        io.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.04 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.dataset.seen = "true"; });
  }

  /* ------------------------------------------------------------- back to top */
  var totop = doc.querySelector(".totop");
  if (totop) {
    var toggleTop = function () {
      totop.dataset.show = window.scrollY > window.innerHeight * 0.9 ? "true" : "false";
    };
    toggleTop();
    window.addEventListener("scroll", toggleTop, { passive: true });
    totop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* --------------------------------------------------------- language switch */
  var LANG_KEY = "kff-lang";
  var root = doc.documentElement;

  function placeholders(lang) {
    doc.querySelectorAll("input[data-ph-en]").forEach(function (el) {
      var v = el.getAttribute("data-ph-" + lang);
      if (v) el.setAttribute("placeholder", v);
    });
  }

  function setLang(lang, remember) {
    lang = lang === "ko" ? "ko" : "en";
    root.setAttribute("data-lang", lang);
    root.setAttribute("lang", lang);
    placeholders(lang);
    var btn = doc.querySelector("[data-lang-toggle]");
    if (btn) {
      btn.setAttribute("aria-pressed", lang === "ko" ? "true" : "false");
      btn.setAttribute("aria-label", lang === "ko" ? "Switch to English" : "Switch to Korean");
    }
    if (remember) {
      try { localStorage.setItem(LANG_KEY, lang); } catch (e) { /* private mode */ }
    }
  }

  var stored = null;
  try { stored = localStorage.getItem(LANG_KEY); } catch (e) { /* ignore */ }
  if (!stored && (navigator.language || "").toLowerCase().indexOf("ko") === 0) stored = "ko";
  setLang(stored || "en", false);

  var langBtn = doc.querySelector("[data-lang-toggle]");
  if (langBtn) {
    langBtn.addEventListener("click", function () {
      setLang(root.getAttribute("data-lang") === "ko" ? "en" : "ko", true);
    });
  }

  /* -------------------------------------------------- filter the roster table */
  var rSearch = doc.querySelector(".roster__search");
  if (rSearch) {
    var rows = Array.prototype.slice.call(doc.querySelectorAll(".roster__table tbody tr"));
    var shown = doc.querySelector(".roster__shown");
    var none = doc.querySelector(".roster__empty");
    var timer = null;

    var apply = function () {
      var q = rSearch.value.trim().toLowerCase();
      var n = 0;
      for (var i = 0; i < rows.length; i++) {
        var hit = !q || rows[i].textContent.toLowerCase().indexOf(q) !== -1;
        if (rows[i].hidden === hit) rows[i].hidden = !hit;
        if (hit) n++;
      }
      if (shown) shown.textContent = q ? n + " / " + rows.length : "";
      if (none) none.hidden = n !== 0;
    };

    /* debounced: these tables run to several thousand rows */
    rSearch.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(apply, 120);
    });
  }

  /* ------------------------------------------- filter the on-page name index */
  var search = doc.querySelector(".pageindex__search");
  if (search) {
    var entries = Array.prototype.slice.call(doc.querySelectorAll(".pageindex__list li"));
    var empty = doc.querySelector(".pageindex__empty");
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      entries.forEach(function (li) {
        var hit = !q || li.textContent.toLowerCase().indexOf(q) !== -1;
        li.hidden = !hit;
        if (hit) shown++;
      });
      if (empty) empty.hidden = shown !== 0;
    });
  }
})();
