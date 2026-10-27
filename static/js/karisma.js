/* Karisma front-end behaviour: toasts, progress, save toggles, amount chips, loading states */
(function () {
  "use strict";

  function showToast(message, type) {
    var container = document.getElementById("toastContainer");
    if (!container || !window.bootstrap) return;
    var el = document.createElement("div");
    el.className = "toast k-toast align-items-center border-0 text-bg-" + (type || "success");
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    el.innerHTML = '<div class="d-flex"><div class="toast-body fw-semibold"></div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>';
    el.querySelector(".toast-body").textContent = message;
    container.appendChild(el);
    var toast = new bootstrap.Toast(el, { delay: 4500 });
    el.addEventListener("hidden.bs.toast", function () { el.remove(); });
    toast.show();
  }
  window.karismaToast = showToast;

  // Django messages -> toasts
  document.querySelectorAll(".k-toast").forEach(function (el) {
    if (window.bootstrap) new bootstrap.Toast(el, { delay: 5500 }).show();
  });

  // Navbar shadow on scroll
  var nav = document.querySelector(".k-navbar");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // Animated progress bars
  var bars = document.querySelectorAll(".k-progress-bar[data-progress]");
  function fillBar(bar) { bar.style.width = Math.min(100, Math.max(0, parseFloat(bar.dataset.progress) || 0)) + "%"; }
  if ("IntersectionObserver" in window) {
    var barObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { fillBar(entry.target); barObserver.unobserve(entry.target); }
      });
    }, { threshold: 0.2 });
    bars.forEach(function (bar) { barObserver.observe(bar); });
  } else { bars.forEach(fillBar); }

  // Reveal on scroll
  var reveals = document.querySelectorAll("[data-reveal]");
  if ("IntersectionObserver" in window) {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("revealed"); revealObserver.unobserve(entry.target); }
      });
    }, { threshold: 0.08 });
    reveals.forEach(function (el, i) { el.style.transitionDelay = (i % 6) * 60 + "ms"; revealObserver.observe(el); });
  } else { reveals.forEach(function (el) { el.classList.add("revealed"); }); }

  // Count-up numbers
  document.querySelectorAll("[data-countup]").forEach(function (el) {
    var target = parseFloat(el.dataset.countup) || 0;
    var prefix = el.dataset.prefix || "";
    var suffix = el.dataset.suffix || "";
    var format = function (n) { return prefix + Math.round(n).toLocaleString("en-IN") + suffix; };
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || target === 0) { el.textContent = format(target); return; }
    var start = null, duration = 1400;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      el.textContent = format(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    }
    var started = false;
    var io = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting && !started) { started = true; requestAnimationFrame(step); io.disconnect(); }
    });
    io.observe(el);
  });

  // Save / follow toggle (AJAX with graceful fallback to normal POST)
  document.addEventListener("submit", function (event) {
    var form = event.target.closest(".js-toggle-form");
    if (!form || !window.fetch) return;
    event.preventDefault();
    var btn = form.querySelector("button");
    btn.disabled = true;
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin"
    }).then(function (res) {
      if (res.redirected && res.url.indexOf("/login") !== -1) { window.location.href = res.url; return null; }
      return res.json();
    }).then(function (data) {
      if (!data) return;
      btn.classList.toggle("is-active", data.saved);
      btn.setAttribute("aria-pressed", data.saved ? "true" : "false");
      var icon = btn.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-bookmark-heart-fill", data.saved);
        icon.classList.toggle("bi-bookmark-heart", !data.saved);
      }
      var label = btn.querySelector(".js-label");
      if (label) label.textContent = data.saved ? btn.dataset.on : btn.dataset.off;
      showToast(data.message, "success");
    }).catch(function () {
      showToast("Something went wrong. Please try again.", "danger");
    }).finally(function () { btn.disabled = false; });
  });

  // Quick-amount chips
  document.querySelectorAll("[data-amount-target]").forEach(function (group) {
    var input = document.querySelector(group.dataset.amountTarget);
    if (!input) return;
    var chips = group.querySelectorAll(".amount-chip");
    function sync() {
      chips.forEach(function (c) { c.classList.toggle("active", c.dataset.amount === String(parseInt(input.value, 10))); });
    }
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () { input.value = chip.dataset.amount; sync(); input.focus(); });
    });
    input.addEventListener("input", sync);
    sync();
  });

  // Loading state on form submit
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.classList.contains("js-toggle-form") || form.hasAttribute("data-no-loading")) return;
    var btn = form.querySelector('button[type="submit"]:not([data-no-loading])');
    if (!btn || btn.classList.contains("is-loading")) return;
    window.setTimeout(function () {
      btn.classList.add("is-loading");
      btn.dataset.originalHtml = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Please wait…';
    }, 0);
  });
  // Restore buttons if the page is restored from bfcache
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    document.querySelectorAll(".btn.is-loading").forEach(function (b) {
      b.classList.remove("is-loading");
      if (b.dataset.originalHtml) b.innerHTML = b.dataset.originalHtml;
    });
  });
})();
