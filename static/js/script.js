document.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.querySelector(".menu-toggle");
  const sidebar = document.querySelector(".sidebar");
  if (menuButton && sidebar) {
    menuButton.addEventListener("click", () => {
      const isOpen = sidebar.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(isOpen));
    });
    document.addEventListener("click", (event) => {
      if (window.innerWidth <= 760 && sidebar.classList.contains("open")
          && !sidebar.contains(event.target) && !menuButton.contains(event.target)) {
        sidebar.classList.remove("open");
        menuButton.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll("form[data-submit-loading]").forEach((form) => {
    form.addEventListener("submit", () => {
      const label = form.querySelector(".button-label");
      const loading = form.querySelector(".button-loading");
      const button = form.querySelector('button[type="submit"]');
      if (label && loading && button) {
        label.classList.add("d-none");
        loading.classList.remove("d-none");
        button.disabled = true;
      }
    });
  });

  const dataNode = document.getElementById("distribution-data");
  const canvas = document.getElementById("performanceChart");
  if (dataNode && canvas && window.Chart) {
    const distribution = JSON.parse(dataNode.textContent);
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: Object.keys(distribution),
        datasets: [{
          data: Object.values(distribution),
          backgroundColor: ["#49c9a5", "#6474ed", "#f0b857", "#e58b9b"],
          borderRadius: 6,
          maxBarThickness: 45,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { displayColors: false } },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { color: "#909bae", font: { family: "DM Sans", size: 9 } } },
          y: { beginAtZero: true, suggestedMax: 5, ticks: { precision: 0, color: "#a4adbb", font: { family: "DM Sans", size: 9 } }, grid: { color: "#eff1f6", drawTicks: false }, border: { display: false } },
        },
      },
    });
  }

  const trendNode = document.getElementById("trend-data");
  const trendCanvas = document.getElementById("trendChart");
  if (trendNode && trendCanvas && window.Chart) {
    const trend = JSON.parse(trendNode.textContent);
    new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: trend.labels,
        datasets: [{
          data: trend.marks,
          borderColor: "#6573e8",
          backgroundColor: "rgba(101, 115, 232, .10)",
          fill: true,
          tension: .35,
          pointRadius: 3,
          pointBackgroundColor: "#6573e8",
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { displayColors: false } },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { color: "#909bae", font: { family: "DM Sans", size: 9 }, maxRotation: 0, autoSkip: true } },
          y: { min: 0, max: 100, ticks: { stepSize: 25, color: "#a4adbb", font: { family: "DM Sans", size: 9 } }, grid: { color: "#eff1f6", drawTicks: false }, border: { display: false } },
        },
      },
    });
  }
});
