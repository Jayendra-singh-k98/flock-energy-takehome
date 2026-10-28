// Urja Meter Ops Modern Web Dashboard Client

let currentPage = 1;
const pageSize = 15;
let mapInstance = null;
let mapMarkers = [];
let telemetryChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initEventListeners();
  loadOverview();
  loadMeters(1);
  loadTransformers();
});

// Tab switching logic
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-content");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }

      if (targetId === "tab-map") {
        setTimeout(initMap, 200);
      } else if (targetId === "tab-hierarchy") {
        loadHierarchy();
      } else if (targetId === "tab-telemetry" && !telemetryChartInstance) {
        loadTelemetry("J100000");
      }
    });
  });
}

function initEventListeners() {
  // Filter inputs
  const debouncedSearch = debounce(() => loadMeters(1), 300);
  document.getElementById("filter-q").addEventListener("input", debouncedSearch);
  document.getElementById("filter-make").addEventListener("change", () => loadMeters(1));
  document.getElementById("filter-phase").addEventListener("change", () => loadMeters(1));
  document.getElementById("filter-status").addEventListener("change", () => loadMeters(1));
  document.getElementById("filter-dt").addEventListener("change", () => loadMeters(1));

  // Pagination buttons
  document.getElementById("btn-prev").addEventListener("click", () => {
    if (currentPage > 1) loadMeters(currentPage - 1);
  });
  document.getElementById("btn-next").addEventListener("click", () => {
    loadMeters(currentPage + 1);
  });

  // Sync button
  document.getElementById("btn-sync").addEventListener("click", async () => {
    const btn = document.getElementById("btn-sync");
    btn.disabled = true;
    btn.innerText = "↻ Syncing...";
    try {
      const res = await fetch("/api/v1/sync", { method: "POST" });
      const data = await res.json();
      alert(`Synchronized ${data.meters_synced} meters and ${data.transformers_synced} transformers.`);
      loadOverview();
      loadMeters(1);
      loadTransformers();
      if (mapInstance) loadMapMarkers();
    } catch (err) {
      alert("Sync failed: " + err.message);
    } finally {
      btn.disabled = false;
      btn.innerText = "↻ Sync Now";
    }
  });

  // Telemetry load button
  document.getElementById("btn-load-telemetry").addEventListener("click", () => {
    const meterId = document.getElementById("telemetry-meter-input").value.trim();
    if (meterId) {
      loadTelemetry(meterId);
    }
  });

  // Modal close
  document.getElementById("modal-close-btn").addEventListener("click", closeModal);
  document.getElementById("detail-modal").addEventListener("click", (e) => {
    if (e.target.id === "detail-modal") closeModal();
  });
}

// Load high-level overview metrics
async function loadOverview() {
  try {
    const res = await fetch("/api/v1/analytics/overview");
    const data = await res.json();

    document.getElementById("kpi-total-meters").innerText = data.total_meters.toLocaleString();
    document.getElementById("kpi-installed").innerText = (data.status_distribution["Installed"] || 0).toLocaleString();
    document.getElementById("kpi-faulty").innerText = (data.status_distribution["Faulty"] || 0).toLocaleString();
    document.getElementById("kpi-decommissioned").innerText = (data.status_distribution["Decommissioned"] || 0).toLocaleString();
    document.getElementById("kpi-dts").innerText = data.total_transformers.toLocaleString();
    document.getElementById("kpi-capacity").innerText = `Total Capacity: ${data.total_transformer_capacity_kva.toLocaleString()} kVA`;
  } catch (err) {
    console.error("Failed to load overview:", err);
  }
}

// Load paginated meters table
async function loadMeters(page = 1) {
  currentPage = page;
  const q = document.getElementById("filter-q").value.trim();
  const make = document.getElementById("filter-make").value;
  const phase = document.getElementById("filter-phase").value;
  const status = document.getElementById("filter-status").value;
  const dtCode = document.getElementById("filter-dt").value;

  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (q) params.append("q", q);
  if (make) params.append("make", make);
  if (phase) params.append("phase_type", phase);
  if (status) params.append("install_status", status);
  if (dtCode) params.append("dt_code", dtCode);

  const tbody = document.getElementById("meters-table-body");
  tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 24px;">Fetching meters...</td></tr>`;

  try {
    const res = await fetch(`/api/v1/meters?${params.toString()}`);
    const result = await res.json();

    tbody.innerHTML = "";
    if (!result.data || result.data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 24px; color: var(--text-dim);">No matching meters found.</td></tr>`;
      return;
    }

    result.data.forEach((m) => {
      const tr = document.createElement("tr");

      let badgeClass = "badge-neutral";
      if (m.install_status.toLowerCase() === "installed") badgeClass = "badge-success";
      else if (m.install_status.toLowerCase() === "faulty") badgeClass = "badge-danger";
      else if (m.install_status.toLowerCase() === "decommissioned") badgeClass = "badge-neutral";

      tr.innerHTML = `
        <td><a class="meter-link" onclick="openMeterModal('${m.meter_id}')">${m.meter_id}</a></td>
        <td><code>${m.serial_no}</code></td>
        <td>${m.make}</td>
        <td>${m.phase_type}</td>
        <td><span class="badge ${badgeClass}">${m.install_status}</span></td>
        <td><span class="badge badge-neutral">${m.dt_code}</span></td>
        <td><small style="color:var(--text-dim);">${m.build || "legacy"}</small></td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="viewTelemetry('${m.meter_id}')">📈 Energy</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    const p = result.pagination;
    document.getElementById("page-info").innerText = `Page ${p.page} of ${Math.max(1, p.total_pages)} (${p.total_items} meters)`;
    document.getElementById("btn-prev").disabled = !p.has_prev;
    document.getElementById("btn-next").disabled = !p.has_next;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--accent-red); padding: 24px;">Error: ${err.message}</td></tr>`;
  }
}

// Load transformers
async function loadTransformers() {
  try {
    const res = await fetch("/api/v1/transformers");
    const dts = await res.json();

    // Populate DT filter options
    const dtSelect = document.getElementById("filter-dt");
    dtSelect.innerHTML = `<option value="">All DTs</option>`;
    dts.forEach((dt) => {
      const opt = document.createElement("option");
      opt.value = dt.code;
      opt.textContent = `${dt.code} — ${dt.name}`;
      dtSelect.appendChild(opt);
    });

    // Populate transformers table
    const tbody = document.getElementById("transformers-table-body");
    tbody.innerHTML = "";
    dts.forEach((dt) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${dt.code}</strong></td>
        <td>${dt.name}</td>
        <td><span class="badge badge-neutral">${dt.feeder_code}</span></td>
        <td>${dt.capacity_kva} kVA</td>
        <td><strong>${dt.connected_meters_count}</strong></td>
        <td><span class="badge badge-success">${dt.installed_meters_count}</span></td>
        <td><span class="badge badge-danger">${dt.faulty_meters_count}</span></td>
        <td><span class="badge badge-neutral">${dt.decommissioned_meters_count}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load transformers:", err);
  }
}

// Leaflet Map Initialization
function initMap() {
  if (mapInstance) {
    mapInstance.invalidateSize();
    return;
  }

  // Jaipur center coordinates
  mapInstance = L.map("meters-map").setView([26.9124, 75.7873], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '© OpenStreetMap contributors',
  }).addTo(mapInstance);

  loadMapMarkers();
}

async function loadMapMarkers() {
  try {
    // Fetch all meters
    const res = await fetch("/api/v1/meters?page=1&page_size=100");
    const result = await res.json();
    const meters = result.data || [];

    mapMarkers.forEach((m) => mapInstance.removeLayer(m));
    mapMarkers = [];

    meters.forEach((m) => {
      if (m.geo && m.geo.latitude && m.geo.longitude) {
        let color = "#10b981"; // Installed = green
        if (m.install_status.toLowerCase() === "faulty") color = "#ef4444";
        if (m.install_status.toLowerCase() === "decommissioned") color = "#94a3b8";

        const marker = L.circleMarker([m.geo.latitude, m.geo.longitude], {
          radius: 6,
          fillColor: color,
          color: "#fff",
          weight: 1.5,
          opacity: 1,
          fillOpacity: 0.85,
        });

        marker.bindPopup(`
          <div style="font-family:sans-serif; min-width: 160px;">
            <strong style="color:#0f172a; font-size:14px;">${m.meter_id}</strong>
            <p style="margin: 4px 0; color:#475569; font-size:12px;">Serial: ${m.serial_no}</p>
            <p style="margin: 4px 0; color:#475569; font-size:12px;">Make: ${m.make} (${m.phase_type})</p>
            <p style="margin: 4px 0; color:#475569; font-size:12px;">DT: ${m.dt_code}</p>
            <p style="margin: 4px 0; font-size:12px;">Status: <strong>${m.install_status}</strong></p>
            <button onclick="viewTelemetry('${m.meter_id}')" style="margin-top:6px; background:#2563eb; color:#fff; border:none; padding:4px 8px; border-radius:4px; font-size:11px; cursor:pointer;">View Telemetry</button>
          </div>
        `);

        marker.addTo(mapInstance);
        mapMarkers.push(marker);
      }
    });
  } catch (err) {
    console.error("Failed to load map markers:", err);
  }
}

// Telemetry & Consumption
async function loadTelemetry(meterId) {
  document.getElementById("telemetry-meter-input").value = meterId;
  const cards = document.getElementById("telemetry-summary-cards");
  cards.style.opacity = "0.5";

  try {
    const res = await fetch(`/api/v1/meters/${meterId}/energy`);
    if (!res.ok) throw new Error(`Status ${res.status}`);
    const data = await res.json();

    document.getElementById("telemetry-readings-count").innerText = data.reading_count.toLocaleString();
    document.getElementById("telemetry-kwh-delta").innerText = data.total_active_kwh_delta !== null ? `${data.total_active_kwh_delta} kWh` : "—";
    document.getElementById("telemetry-avg-voltage").innerText = data.avg_voltage_r !== null ? `${data.avg_voltage_r} V` : "—";
    document.getElementById("telemetry-voltage-range").innerText = `Min: ${data.min_voltage_r || "—"}V | Max: ${data.max_voltage_r || "—"}V`;

    const anomalyBadge = document.getElementById("telemetry-anomaly-badge");
    if (data.voltage_anomaly) {
      anomalyBadge.innerHTML = `<span class="badge badge-danger">⚠️ Deviation Detected</span>`;
    } else {
      anomalyBadge.innerHTML = `<span class="badge badge-success">✓ Normal Voltage</span>`;
    }

    renderChart(data.readings || []);
  } catch (err) {
    alert(`Could not load telemetry for ${meterId}: ${err.message}`);
  } finally {
    cards.style.opacity = "1";
  }
}

function renderChart(readings) {
  const ctx = document.getElementById("telemetry-chart").getContext("2d");
  if (telemetryChartInstance) {
    telemetryChartInstance.destroy();
  }

  // Downsample if many readings for smooth rendering
  const stride = Math.max(1, Math.floor(readings.length / 50));
  const sampled = readings.filter((_, idx) => idx % stride === 0);

  const labels = sampled.map((r) => r.timestamp);
  const kwhData = sampled.map((r) => r.kwh);
  const voltData = sampled.map((r) => r.volt_r);

  telemetryChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Active Energy (kWh)",
          data: kwhData,
          borderColor: "#06b6d4",
          backgroundColor: "rgba(6, 182, 212, 0.1)",
          yAxisID: "yKwh",
          tension: 0.2,
          fill: true,
        },
        {
          label: "Phase R Voltage (V)",
          data: voltData,
          borderColor: "#f59e0b",
          backgroundColor: "transparent",
          yAxisID: "yVolt",
          borderDash: [5, 5],
          tension: 0.2,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#94a3b8" } },
      },
      scales: {
        x: {
          ticks: { color: "#64748b", maxTicksLimit: 10 },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
        },
        yKwh: {
          type: "linear",
          position: "left",
          ticks: { color: "#06b6d4" },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
        },
        yVolt: {
          type: "linear",
          position: "right",
          ticks: { color: "#f59e0b" },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

function viewTelemetry(meterId) {
  closeModal();
  document.querySelector(`[data-tab="tab-telemetry"]`).click();
  loadTelemetry(meterId);
}

// Network Hierarchy Tree
async function loadHierarchy() {
  const container = document.getElementById("hierarchy-tree-root");
  try {
    const res = await fetch("/api/v1/hierarchy");
    const data = await res.json();

    container.innerHTML = "";
    data.root_zones.forEach((zone) => {
      container.appendChild(createTreeNodeElement(zone));
    });
  } catch (err) {
    container.innerHTML = `<p style="color:var(--accent-red);">Failed to load hierarchy: ${err.message}</p>`;
  }
}

function createTreeNodeElement(node) {
  const el = document.createElement("div");
  el.className = "tree-node";

  const header = document.createElement("div");
  header.className = "tree-header";

  const isLeaf = !node.children || node.children.length === 0;
  const icon = isLeaf ? "⚡" : "📁";

  header.innerHTML = `
    <span>${icon}</span>
    <strong>${node.name}</strong>
    <span class="badge badge-neutral" style="font-size:0.7rem;">${node.level.toUpperCase()}: ${node.code}</span>
    <span style="font-size:0.75rem; color:var(--text-dim); margin-left:auto;">${node.meter_count} meters</span>
  `;

  el.appendChild(header);

  if (!isLeaf) {
    const childContainer = document.createElement("div");
    childContainer.style.display = "block";
    node.children.forEach((child) => {
      childContainer.appendChild(createTreeNodeElement(child));
    });
    el.appendChild(childContainer);

    header.addEventListener("click", () => {
      childContainer.style.display = childContainer.style.display === "none" ? "block" : "none";
    });
  }

  return el;
}

// Meter Detail Modal
async function openMeterModal(meterId) {
  const modal = document.getElementById("detail-modal");
  const content = document.getElementById("modal-content");
  document.getElementById("modal-meter-title").innerText = `Meter ${meterId}`;
  content.innerHTML = `<p style="color:var(--text-muted);">Fetching details...</p>`;
  modal.classList.add("active");

  try {
    const res = await fetch(`/api/v1/meters/${meterId}`);
    const m = await res.json();

    const h = m.hierarchy || {};
    content.innerHTML = `
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div style="background:var(--bg-primary); padding:16px; border-radius:10px; border:1px solid var(--border-color);">
          <h4 style="color:var(--accent-cyan); margin-bottom:10px; font-size:0.85rem; text-transform:uppercase;">Nameplate Specification</h4>
          <p style="margin-bottom:6px;"><strong>Serial:</strong> <code>${m.serial_no}</code></p>
          <p style="margin-bottom:6px;"><strong>Make:</strong> ${m.make}</p>
          <p style="margin-bottom:6px;"><strong>Phase:</strong> ${m.phase_type}</p>
          <p style="margin-bottom:6px;"><strong>Install Status:</strong> <span class="badge badge-success">${m.install_status}</span></p>
          <p style="margin-bottom:6px;"><strong>Installation Type:</strong> ${m.install_type || "Whole Current"}</p>
          <p><strong>Build Type:</strong> ${m.build || "legacy"}</p>
        </div>

        <div style="background:var(--bg-primary); padding:16px; border-radius:10px; border:1px solid var(--border-color);">
          <h4 style="color:var(--accent-cyan); margin-bottom:10px; font-size:0.85rem; text-transform:uppercase;">Grid Topology</h4>
          <p style="margin-bottom:6px;"><strong>Zone:</strong> ${h.zone ? h.zone.name + ' (' + h.zone.code + ')' : '—'}</p>
          <p style="margin-bottom:6px;"><strong>Substation:</strong> ${h.substation ? h.substation.name + ' (' + h.substation.code + ')' : '—'}</p>
          <p style="margin-bottom:6px;"><strong>Feeder:</strong> ${h.feeder ? h.feeder.name + ' (' + h.feeder.code + ')' : '—'}</p>
          <p style="margin-bottom:6px;"><strong>DT:</strong> ${h.dt ? h.dt.name + ' (' + h.dt.code + ')' : m.dt_code}</p>
          <p><strong>Coordinates:</strong> ${m.geo ? `${m.geo.latitude.toFixed(5)}, ${m.geo.longitude.toFixed(5)}` : 'Unavailable'}</p>
        </div>
      </div>

      <div style="margin-top:20px; display:flex; justify-content:flex-end; gap:12px;">
        <button class="btn btn-primary" onclick="viewTelemetry('${meterId}')">Open Telemetry Readings →</button>
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<p style="color:var(--accent-red);">Error: ${err.message}</p>`;
  }
}

function closeModal() {
  document.getElementById("detail-modal").classList.remove("active");
}

function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
