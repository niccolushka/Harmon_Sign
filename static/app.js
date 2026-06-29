const state = { harmonics: [], visualization: null };
const fields = ["amplitude", "frequency", "phase", "harmonic"];
const sliderPairs = fields.map((field) => [field, `${field}-slider`]);
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
  syncSlidersFromInputs();
}

function syncSlidersFromInputs() {
  sliderPairs.forEach(([inputId, sliderId]) => {
    document.getElementById(sliderId).value = document.getElementById(inputId).value;
  });
}

function setupSliderSync() {
  sliderPairs.forEach(([inputId, sliderId]) => {
    const input = document.getElementById(inputId);
    const slider = document.getElementById(sliderId);
    slider.addEventListener("input", () => {
      input.value = slider.value;
      setMessage("");
    });
    input.addEventListener("input", () => {
      slider.value = input.value;
      setMessage("");
    });
  });
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

function setupCanvas(canvas, preferredWidth = 900) {
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(canvas.parentElement.clientWidth, preferredWidth);
  const height = canvas.clientHeight;
  canvas.style.width = `${width}px`;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width, height };
}

function drawAxes(context, width, height, xLabels = [], yMin = -1, yMax = 1) {
  const left = 52;
  const bottom = height - 34;
  context.strokeStyle = "rgba(255,255,255,0.14)";
  context.fillStyle = "#9fb0c7";
  context.font = "12px sans-serif";
  context.lineWidth = 1;

  context.beginPath();
  context.moveTo(left, 16);
  context.lineTo(left, bottom);
  context.lineTo(width - 12, bottom);
  context.stroke();

  const yTicks = 4;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const y = 16 + (tick / yTicks) * (bottom - 16);
    const value = yMax - (tick / yTicks) * (yMax - yMin);
    context.strokeStyle = "rgba(255,255,255,0.08)";
    context.beginPath();
    context.moveTo(left, y);
    context.lineTo(width - 12, y);
    context.stroke();
    context.fillText(value.toFixed(2), 6, y + 4);
  }

  xLabels.forEach(({ x, label }) => {
    context.strokeStyle = "rgba(255,255,255,0.08)";
    context.beginPath();
    context.moveTo(x, 16);
    context.lineTo(x, bottom);
    context.stroke();
    context.fillText(label, x - 14, height - 12);
  });
}

function drawLineChart(canvas, labels, values, color) {
  const preferredWidth = Math.max(900, labels.length * 2.2);
  const { context, width, height } = setupCanvas(canvas, preferredWidth);
  context.clearRect(0, 0, width, height);
  const min = Math.min(...values, -1);
  const max = Math.max(...values, 1);
  const xTicks = Array.from({ length: 6 }, (_, tick) => {
    const index = Math.round((tick / 5) * (labels.length - 1));
    return { x: 52 + (index / (labels.length - 1)) * (width - 68), label: `${labels[index].toFixed(2)}с` };
  });
  drawAxes(context, width, height, xTicks, min, max);
  context.strokeStyle = color;
  context.lineWidth = 2;
  context.beginPath();
  values.forEach((value, index) => {
    const x = 52 + (index / (labels.length - 1)) * (width - 68);
    const y = 16 + ((max - value) / (max - min || 1)) * (height - 50);
    index === 0 ? context.moveTo(x, y) : context.lineTo(x, y);
  });
  context.stroke();
}

function drawSpectrum(canvas, points, color) {
  const preferredWidth = Math.max(900, points.length * 130);
  const { context, width, height } = setupCanvas(canvas, preferredWidth);
  context.clearRect(0, 0, width, height);
  const maxFrequency = Math.max(...points.map((point) => point.frequency), 1);
  const maxAmplitude = Math.max(...points.map((point) => point.amplitude), 1);
  const xTicks = Array.from({ length: 6 }, (_, tick) => {
    const value = (tick / 5) * maxFrequency;
    return { x: 52 + (value / maxFrequency) * (width - 80), label: `${value.toFixed(1)}Гц` };
  });
  drawAxes(context, width, height, xTicks, 0, maxAmplitude);
  points.forEach((point) => {
    const x = 52 + (point.frequency / maxFrequency) * (width - 80);
    const barHeight = (point.amplitude / maxAmplitude) * (height - 58);
    context.fillStyle = color;
    context.fillRect(x - 6, height - 34 - barHeight, 12, barHeight);
    context.fillStyle = "#9fb0c7";
    context.font = "12px sans-serif";
    context.fillText(`${point.frequency}Гц`, Math.max(54, x - 20), height - 12);
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
setupSliderSync();
window.addEventListener("resize", renderCharts);
loadData().catch((error) => setMessage(error.message));
