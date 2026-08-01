document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) {
        return;
    }

    const button = form.querySelector("button[type='submit']");
    if (button instanceof HTMLButtonElement) {
        button.disabled = true;
        button.dataset.originalText = button.textContent || "";
        button.textContent = "Working...";
    }
});

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#039;");
}

function dash(value) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }

    return value;
}

function formatKwh(value, digits = 3) {
    const numeric = Number(value ?? 0);
    return `${numeric.toFixed(digits)} kWh`;
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function renderDashboardMetrics(statistics) {
    setText("metric-session-count", statistics.session_count ?? 0);
    setText("metric-total-energy", formatKwh(statistics.total_energy_kwh));
    setText("metric-today-energy", formatKwh(statistics.today_energy_kwh));
    setText("metric-month-energy", formatKwh(statistics.month_energy_kwh));
}

function renderDashboardChargers(chargers) {
    const body = document.getElementById("dashboard-chargers-body");
    if (!body) {
        return;
    }

    body.innerHTML = chargers.map((charger) => {
        const name = charger.display_name || charger.charger_id;
        const visibleLabel = charger.visible ? "Visible" : "Offline";
        const visibleClass = charger.visible ? "ok" : "muted";

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(name)}</strong>
                    <small>${escapeHtml(charger.ssid)}</small>
                </td>
                <td>
                    <span class="status ${visibleClass}"></span>
                    ${visibleLabel}
                </td>
                <td>${escapeHtml(dash(charger.last_signal))}</td>
                <td>${escapeHtml(dash(charger.last_scrape_success_at))}</td>
            </tr>
        `;
    }).join("");
}

function renderBarRows(id, rows, options) {
    const container = document.getElementById(id);
    if (!container) {
        return;
    }

    if (!rows.length) {
        container.innerHTML = `<p class="muted-copy">${options.emptyText}</p>`;
        return;
    }

    const maxEnergy = Math.max(
        ...rows.map((row) => Number(row.energy_kwh ?? 0)),
        0,
    );

    container.innerHTML = rows.map((row) => {
        const energy = Number(row.energy_kwh ?? 0);
        const width = maxEnergy === 0 ? 0 : (energy / maxEnergy) * 100;
        return `
            <div class="bar-row">
                <span>${escapeHtml(options.label(row))}</span>
                <div class="bar-track">
                    <div class="bar-fill" style="width: ${width}%"></div>
                </div>
                <strong>${energy.toFixed(2)}</strong>
            </div>
        `;
    }).join("");
}

function renderDashboardSessions(sessions) {
    const body = document.getElementById("dashboard-sessions-body");
    if (!body) {
        return;
    }

    const recent = sessions.slice(0, 10);
    if (!recent.length) {
        body.innerHTML = `
            <tr>
                <td colspan="6" class="empty">No sessions collected yet.</td>
            </tr>
        `;
        return;
    }

    body.innerHTML = recent.map((session) => `
        <tr>
            <td>${escapeHtml(session.session_id)}</td>
            <td>CHARGER_${escapeHtml(session.charger_id)}</td>
            <td>${escapeHtml(dash(session.session_start_local))}</td>
            <td>${escapeHtml(dash(session.energy_kwh))}</td>
            <td>${escapeHtml(dash(session.duration))}</td>
            <td>${escapeHtml(dash(session.cost))}</td>
        </tr>
    `).join("");
}

function renderDashboardRuns(runs) {
    const body = document.getElementById("dashboard-runs-body");
    if (!body) {
        return;
    }

    if (!runs.length) {
        body.innerHTML = `
            <tr>
                <td colspan="6" class="empty">No collection runs yet.</td>
            </tr>
        `;
        return;
    }

    body.innerHTML = runs.map((run) => `
        <tr>
            <td>${escapeHtml(dash(run.started_at))}</td>
            <td>CHARGER_${escapeHtml(run.charger_id)}</td>
            <td>${escapeHtml(dash(run.status))}</td>
            <td>${escapeHtml(dash(run.records_inserted))}</td>
            <td>${escapeHtml(dash(run.records_duplicate))}</td>
            <td>${escapeHtml(dash(run.error_message))}</td>
        </tr>
    `).join("");
}

function setDashboardRefreshStatus(message, isError = false) {
    const status = document.getElementById("dashboard-refresh-status");
    if (!status) {
        return;
    }

    status.textContent = message;
    status.classList.toggle("refresh-error", isError);
}

function initializeDashboardAutoRefresh() {
    if (!document.getElementById("dashboard-chargers-body")) {
        return;
    }

    let refreshing = false;

    async function refreshDashboard() {
        if (refreshing) {
            return;
        }

        refreshing = true;
        try {
            const response = await fetch("/api/fleet", { cache: "no-store" });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            renderDashboardMetrics(data.statistics);
            renderDashboardChargers(data.chargers);
            renderBarRows(
                "dashboard-energy-by-charger",
                data.statistics.by_charger ?? [],
                {
                    emptyText: "No charger energy data yet.",
                    label: (row) => `CHARGER_${row.charger_id}`,
                },
            );
            renderBarRows(
                "dashboard-daily-energy",
                data.statistics.daily ?? [],
                {
                    emptyText: "No daily energy data yet.",
                    label: (row) => row.day,
                },
            );
            renderDashboardSessions(data.sessions ?? []);
            renderDashboardRuns(data.runs ?? []);
            setDashboardRefreshStatus(
                `Updated ${new Date().toLocaleTimeString()}`,
            );
        } catch (error) {
            setDashboardRefreshStatus(
                `Update failed: ${error.message}`,
                true,
            );
        } finally {
            refreshing = false;
        }
    }

    refreshDashboard();
    window.setInterval(() => {
        if (document.visibilityState === "visible") {
            refreshDashboard();
        }
    }, 15000);
}

document.addEventListener("DOMContentLoaded", initializeDashboardAutoRefresh);

function formatNumber(value, digits = 1, unit = "") {
    if (value === null || value === undefined || value === "") {
        return "-";
    }

    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return "-";
    }

    return `${numeric.toFixed(digits)}${unit ? ` ${unit}` : ""}`;
}

function formatPercent(value) {
    if (value === null || value === undefined || value === "") {
        return "-";
    }

    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return "-";
    }

    return `${numeric.toFixed(1)}%`;
}

function formatSeconds(value) {
    const seconds = Number(value ?? 0);
    if (!Number.isFinite(seconds) || seconds <= 0) {
        return "-";
    }

    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (days > 0) {
        return `${days}d ${hours}h`;
    }
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

function formatTrendValue(value, unit) {
    if (unit === "%") {
        return formatPercent(value);
    }
    if (unit === "MHz") {
        return formatNumber(value, 0, unit);
    }
    return formatNumber(value, unit ? 2 : 2, unit);
}

function renderVitalsCurrent(current) {
    setText("vital-temperature", formatNumber(current.temperature_c, 1, "C"));
    setText("vital-cpu", formatPercent(current.cpu_percent));
    setText("vital-memory", formatPercent(current.memory_used_percent));
    setText("vital-data-disk", formatPercent(current.data_used_percent));
    setText("vital-load", formatNumber(current.load_1, 2));
    setText("vital-frequency", formatNumber(current.cpu_frequency_mhz, 0, "MHz"));
    setText("vital-system-disk", formatPercent(current.root_used_percent));
    setText("vital-throttle", current.throttled_raw || "-");
}

function renderVitalsTrends(trends) {
    const body = document.getElementById("vitals-trends-body");
    if (!body) {
        return;
    }

    body.innerHTML = trends.map((trend) => `
        <tr>
            <td>${escapeHtml(trend.label)}</td>
            <td>${escapeHtml(formatTrendValue(trend.latest, trend.unit))}</td>
            <td>${escapeHtml(formatTrendValue(trend.average, trend.unit))}</td>
            <td>${escapeHtml(formatTrendValue(trend.minimum, trend.unit))}</td>
            <td>${escapeHtml(formatTrendValue(trend.maximum, trend.unit))}</td>
            <td>${escapeHtml(trend.count)}</td>
        </tr>
    `).join("");
}

function renderVitalsSamples(samples) {
    const body = document.getElementById("vitals-samples-body");
    if (!body) {
        return;
    }

    if (!samples.length) {
        body.innerHTML = `
            <tr>
                <td colspan="9" class="empty">No vitals samples recorded yet.</td>
            </tr>
        `;
        return;
    }

    body.innerHTML = samples.map((sample) => `
        <tr>
            <td>${escapeHtml(sample.sampled_at)}</td>
            <td>${escapeHtml(formatNumber(sample.temperature_c, 1, "C"))}</td>
            <td>${escapeHtml(formatPercent(sample.cpu_percent))}</td>
            <td>${escapeHtml(formatNumber(sample.load_1, 2))}</td>
            <td>${escapeHtml(formatPercent(sample.memory_used_percent))}</td>
            <td>${escapeHtml(formatPercent(sample.root_used_percent))}</td>
            <td>${escapeHtml(formatPercent(sample.data_used_percent))}</td>
            <td>${escapeHtml(formatSeconds(sample.uptime_seconds))}</td>
            <td>${escapeHtml(sample.throttled_raw || "-")}</td>
        </tr>
    `).join("");
}

function setVitalsRefreshStatus(message, isError = false) {
    const status = document.getElementById("vitals-refresh-status");
    if (!status) {
        return;
    }

    status.textContent = message;
    status.classList.toggle("refresh-error", isError);
}

function initializeVitalsAutoRefresh() {
    const rangeSelect = document.getElementById("vitals-range");
    if (!(rangeSelect instanceof HTMLSelectElement)) {
        return;
    }

    let refreshing = false;

    async function refreshVitals() {
        if (refreshing) {
            return;
        }

        refreshing = true;
        try {
            const params = new URLSearchParams({ range: rangeSelect.value });
            const response = await fetch(`/api/vitals?${params}`, {
                cache: "no-store",
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            renderVitalsCurrent(data.current);
            renderVitalsTrends(data.trends ?? []);
            renderVitalsSamples(data.samples ?? []);
            setVitalsRefreshStatus(`Updated ${new Date().toLocaleTimeString()}`);
        } catch (error) {
            setVitalsRefreshStatus(`Update failed: ${error.message}`, true);
        } finally {
            refreshing = false;
        }
    }

    rangeSelect.addEventListener("change", refreshVitals);
    refreshVitals();
    window.setInterval(() => {
        if (document.visibilityState === "visible") {
            refreshVitals();
        }
    }, 15000);
}

document.addEventListener("DOMContentLoaded", initializeVitalsAutoRefresh);
