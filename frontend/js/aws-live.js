(() => {
  const base = (window.CLOUDCOST_CONFIG?.API_BASE_URL || "").replace(/\/$/, "");
  if (!base) return;

  const money = (v) => `$${Number(v || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const esc = (v) => String(v ?? "").replace(/[&<>\"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));

  async function get(path) {
    const res = await fetch(`${base}${path}`, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  }

  function replaceDashboard(data) {
    if (!data || !document.querySelector(".kpi-grid")) return;
    const cards = document.querySelectorAll(".kpi-card");
    if (cards[0]) cards[0].querySelector(".kpi-value").textContent = money(data.total_cost);
    if (cards[1]) cards[1].querySelector(".kpi-value").textContent = money(data.forecast_cost);
    if (cards[2]) {
      cards[2].querySelector(".kpi-value").textContent = money(data.budget?.limit || 0);
      const note = cards[2].querySelector(".kpi-note");
      if (note) note.textContent = `${Number(data.budget_used_percent || 0).toFixed(1)}% used`;
      const bar = cards[2].querySelector(".kpi-icon")?.nextElementSibling?.querySelector?.("div");
      if (bar) bar.style.width = `${Math.min(Number(data.budget_used_percent || 0), 100)}%`;
    }
    const change = Number(data.month_change_percent || 0);
    const note = cards[0]?.querySelector(".kpi-note");
    if (note) {
      note.textContent = `${change >= 0 ? "↗" : "↘"} ${Math.abs(change).toFixed(1)}% vs last month`;
      note.className = `kpi-note ${change <= 0 ? "trend-up" : "trend-down"}`;
    }
    const updated = document.getElementById("updated-time");
    if (updated) updated.textContent = "just now";

    const rows = document.querySelectorAll(".legend-row");
    (data.services || []).slice(0, rows.length).forEach((service, i) => {
      const row = rows[i];
      const spans = row.querySelectorAll("span");
      if (spans[1]) spans[1].textContent = service.service.replace(/^Amazon /, "");
      const strong = row.querySelector("strong");
      if (strong) strong.childNodes[0].textContent = money(service.cost) + " ";
    });
  }

  function renderLiveResources(data) {
    const rows = document.querySelectorAll(".data-table tbody tr");
    if (!rows.length || !location.hash.includes("resources")) return;
    data.slice(0, rows.length).forEach((item, i) => {
      const cells = rows[i].querySelectorAll("td");
      if (cells.length >= 5) {
        cells[0].textContent = item.name || "-";
        cells[1].textContent = item.type || "-";
        cells[2].textContent = item.region || "-";
        cells[3].textContent = item.status || "-";
      }
    });
  }

  async function refresh() {
    try {
      const data = await get("/api/dashboard");
      replaceDashboard(data);
      window.dispatchEvent(new CustomEvent("cloudcost:aws-data", { detail: data }));
    } catch (error) {
      console.warn("CloudCost AWS API unavailable; showing dashboard preview.", error);
      const updated = document.getElementById("updated-time");
      if (updated) updated.textContent = "preview mode";
    }
  }

  async function loadResources() {
    try {
      const data = await get("/api/resources");
      renderLiveResources(data);
    } catch (error) {
      console.warn("CloudCost resources API unavailable.", error);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    refresh();
    document.getElementById("refresh-btn")?.addEventListener("click", refresh);
    window.addEventListener("hashchange", () => {
      if (location.hash.includes("resources")) setTimeout(loadResources, 50);
      if (location.hash.includes("dashboard") || !location.hash) setTimeout(refresh, 50);
    });
  });
})();
