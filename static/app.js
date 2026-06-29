const state = { harmonics: [], visualization: null };
const fields = ["amplitude", "frequency", "phase", "harmonic"];
const canvases = {
  signal: document.getElementById("signal-chart"),
  spectrum: document.getElementById("spectrum-chart"),
  pure: document.getElementById("pure-spectrum-chart"),
  filtered: document.getElementById("filtered-spectrum-chart"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Ошибка запроса");
  return data;
}

async function loadData() {
  const data = await requestJson("/api/harmonics");
  state.harmonics = data.harmonics;
  state.visualization = data.visualization;
  renderHarmonics();
  renderCharts();
}

function readForm() {
  return {
    amplitude: Number(document.getElementById("amplitude").value),
    frequency: Number(document.getElementById("frequency").value),
    phase: Number(document.getElementById("phase").value),
    harmonic: Number(document.getElementById("harmonic").value),
    enabled: document.getElementById("enabled").checked,
  };
}

function fillForm(item) {
  document.getElementById("harmonic-id").value = item?.id || "";
  document.getElementById("amplitude").value = item?.amplitude ?? 1;
  document.getElementById("frequency").value = item?.frequency ?? 5;
  document.getElementById("phase").value = item?.phase ?? 0;
  document.getElementById("harmonic").value = item?.harmonic ?? 1;
  document.getElementById("enabled").checked = item?.enabled ?? true;
}

function setMessage(text) {
  document.getElementById("message").textContent = text;
}

function renderHarmonics() {
  const list = document.getElementById("harmonics-list");
  list.innerHTML = "";
  state.harmonics.forEach((item) => {
    const card = document.createElement("div");
    card.className = `harmonic-item${item.enabled ? "" : " disabled"}`;
    card.innerHTML = `
      <strong>Гармоника #${item.id}: A=${item.amplitude}, f=${item.frequency} Гц, φ=${item.phase}°, n=${item.harmonic}</strong>
      <span>${item.enabled ? "Участвует в сумме" : "Отключена"}</span>
      <div class="harmonic-actions">
        <button type="button" data-action="edit">Редактировать</button>
        <button type="button" class="secondary" data-action="toggle">${item.enabled ? "Отключить" : "Включить"}</button>
        <button type="button" class="danger" data-action="delete">Удалить</button>
      </div>`;
    card.querySelector('[data-action="edit"]').addEventListener("click", () => fillForm(item));
    card.querySelector('[data-action="toggle"]').addEventListener("click", () => saveHarmonic(item.id, { ...item, enabled: !item.enabled }));
    card.querySelector('[data-action="delete"]').addEventListener("click", () => deleteHarmonic(item.id));
    list.appendChild(card);
  });
}

async function saveHarmonic(id, payload) {
  const method = id ? "PUT" : "POST";
  const url = id ? `/api/harmonics/${id}` : "/api/harmonics";
  await requestJson(url, { method, body: JSON.stringify(payload) });
  setMessage(id ? "Гармоника обновлена." : "Гармоника добавлена.");
  fillForm(null);
  await loadData();
}

async function deleteHarmonic(id) {
  await requestJson(`/api/harmonics/${id}`, { method: "DELETE" });
  setMessage("Гармоника удалена.");
  await loadData();
}

function setupCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width, height };
}

function drawAxes(context, width, height) {
  context.strokeStyle = "rgba(255,255,255,0.14)";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(42, 16);
  context.lineTo(42, height - 30);
  context.lineTo(width - 12, height - 30);
  context.stroke();
}

function drawLineChart(canvas, labels, values, color) {
  const { context, width, height } = setupCanvas(canvas);
  context.clearRect(0, 0, width, height);
  drawAxes(context, width, height);
  const min = Math.min(...values, -1);
  const max = Math.max(...values, 1);
  context.strokeStyle = color;
  context.lineWidth = 2;
  context.beginPath();
  values.forEach((value, index) => {
    const x = 42 + (index / (labels.length - 1)) * (width - 58);
    const y = 16 + ((max - value) / (max - min || 1)) * (height - 46);
    index === 0 ? context.moveTo(x, y) : context.lineTo(x, y);
  });
  context.stroke();
}

function drawSpectrum(canvas, points, color) {
  const { context, width, height } = setupCanvas(canvas);
  context.clearRect(0, 0, width, height);
  drawAxes(context, width, height);
  const maxFrequency = Math.max(...points.map((point) => point.frequency), 1);
  const maxAmplitude = Math.max(...points.map((point) => point.amplitude), 1);
  points.forEach((point) => {
    const x = 42 + (point.frequency / maxFrequency) * (width - 70);
    const barHeight = (point.amplitude / maxAmplitude) * (height - 54);
    context.fillStyle = color;
    context.fillRect(x - 5, height - 30 - barHeight, 10, barHeight);
    context.fillStyle = "#9fb0c7";
    context.font = "12px sans-serif";
    context.fillText(`${point.frequency}Гц`, Math.max(44, x - 20), height - 10);
  });
}

function renderCharts() {
  const data = state.visualization;
  if (!data) return;
  drawLineChart(canvases.signal, data.time, data.signal, "#38bdf8");
  drawSpectrum(canvases.spectrum, data.spectrum, "#a78bfa");
  drawSpectrum(canvases.pure, data.pureSpectrum, "#34d399");
  drawSpectrum(canvases.filtered, data.filteredSpectrum, "#fbbf24");
  document.getElementById("filter-info").textContent = `Порог низкочастотного фильтра: ${data.cutoffFrequency} Гц`;
}

document.getElementById("harmonic-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const id = document.getElementById("harmonic-id").value;
    await saveHarmonic(id, readForm());
  } catch (error) {
    setMessage(error.message);
  }
});

document.getElementById("reset-form").addEventListener("click", () => fillForm(null));
fields.forEach((field) => document.getElementById(field).addEventListener("input", () => setMessage("")));
window.addEventListener("resize", renderCharts);
loadData().catch((error) => setMessage(error.message));
