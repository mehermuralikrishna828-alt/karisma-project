/* Dashboard charts (Chart.js) */
(function () {
  "use strict";
  var dataEl = document.getElementById("chart-data");
  if (!dataEl || !window.Chart) return;
  var data = JSON.parse(dataEl.textContent);
  var palette = ["#0d9488", "#f59e0b", "#6366f1", "#ec4899", "#0ea5e9", "#84cc16", "#f97316", "#94a3b8"];
  var inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

  Chart.defaults.font.family = '"Plus Jakarta Sans", system-ui, sans-serif';
  Chart.defaults.color = "#64748b";

  function mount(id, config) {
    var canvas = document.getElementById(id);
    if (canvas) new Chart(canvas, config);
  }

  mount("chartTimeline", {
    type: "line",
    data: {
      labels: data.timeline.labels,
      datasets: [{
        label: "Money donated", data: data.timeline.values, fill: true, tension: 0.4,
        borderColor: "#0d9488", backgroundColor: "rgba(13,148,136,.14)", pointBackgroundColor: "#0d9488", pointRadius: 4
      }]
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return inr.format(c.parsed.y); } } } },
      scales: { y: { beginAtZero: true, ticks: { callback: function (v) { return "₹" + v.toLocaleString("en-IN"); } }, grid: { color: "rgba(15,23,42,.06)" } }, x: { grid: { display: false } } }
    }
  });

  mount("chartCategory", {
    type: "doughnut",
    data: { labels: data.category.labels, datasets: [{ data: data.category.values, backgroundColor: palette, borderWidth: 0, hoverOffset: 8 }] },
    options: { maintainAspectRatio: false, cutout: "66%", plugins: { legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true } } } }
  });

  mount("chartDistribution", {
    type: "bar",
    data: { labels: data.distribution.labels, datasets: [{ label: "Contribution", data: data.distribution.values, backgroundColor: palette, borderRadius: 10, borderSkipped: false }] },
    options: {
      indexAxis: "y", maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return inr.format(c.parsed.x); } } } },
      scales: { x: { beginAtZero: true, ticks: { callback: function (v) { return "₹" + v.toLocaleString("en-IN"); } }, grid: { color: "rgba(15,23,42,.06)" } }, y: { grid: { display: false } } }
    }
  });
})();
