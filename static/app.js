const state = { harmonics: [], visualization: null };
const fields = ["amplitude", "frequency", "phase", "harmonic"];
const sliderPairs = fields.map((field) => [field, `${field}-slider`]);
const colors = ["#38bdf8", "#f97316", "#a78bfa", "#34d399", "#f472b6", "#fbbf24"];
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

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function setMode(mode) {
  document.querySelector(`input[name="mode"][value="${mode || "sum"}"]`).checked = true;
}

function readForm() {
  return {
    amplitude: Number(document.getElementById("amplitude").value),
    frequency: Number(document.getElementById("frequency").value),
    phase: Number(document.getElementById("phase").value),
    harmonic: Number(document.getElementById("harmonic").value),
    enabled: document.getElementById("enabled").checked,
    mode: selectedMode(),
  };
}

function fillForm(item) {
  document.getElementById("harmonic-id").value = item?.id || "";
  document.getElementById("amplitude").value = item?.amplitude ?? 1;
  document.getElementById("frequency").value = item?.frequency ?? 5;
  document.getElementById("phase").value = item?.phase ?? 0;
  document.getElementById("harmonic").value = item?.harmonic ?? 1;
  document.getElementById("enabled").checked = item?.enabled ?? true;
  setMode(item?.mode ?? "sum");
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
    const modeText = item.mode === "sum" ? "В сумме" : "Отдельный сигнал";
    card.className = `harmonic-item${item.enabled ? "" : " disabled"}`;
    card.innerHTML = `
      <strong>${modeText} #${item.id}: A=${item.amplitude}, f=${item.frequency} Гц, φ=${item.phase}°, n=${item.harmonic}</strong>
      <span>${item.enabled ? "Активна" : "Отключена"}</span>
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

async function applyPreview() {
  const payload = { ...readForm(), id: document.getElementById("harmonic-id").value };
  const data = await requestJson("/api/preview", { method: "POST", body: JSON.stringify(payload) });
  state.visualization = data.visualization;
  renderCharts();
  setMessage("Предпросмотр применён без сохранения в базу данных.");
}

async function saveHarmonic(id, payload) {
  const method = id ? "PUT" : "POST";
  const url = id ? `/api/harmonics/${id}` : "/api/harmonics";
  await requestJson(url, { method, body: JSON.stringify(payload) });
  setMessage(id ? "Запись обновлена." : "Запись добавлена.");
  fillForm(null);
  await loadData();
}

async function deleteHarmonic(id) {
  await requestJson(`/api/harmonics/${id}`, { method: "DELETE" });
  setMessage("Запись удалена.");
  await loadData();
}

function setupCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.parentElement.clientWidth || 900;
  const height = canvas.clientHeight;
  canvas.style.width = `${width}px`;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { context, width, height };
}

function drawAxes(context, width, height, xLabels = [], yMin = -1, yMax = 1) {
  const left = 62;
  const bottom = height - 40;
  context.strokeStyle = "rgba(255,255,255,0.16)";
  context.fillStyle = "#9fb0c7";
  context.font = "12px sans-serif";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(left, 18);
  context.lineTo(left, bottom);
  context.lineTo(width - 18, bottom);
  context.stroke();

  for (let tick = 0; tick <= 5; tick += 1) {
    const y = 18 + (tick / 5) * (bottom - 18);
    const value = yMax - (tick / 5) * (yMax - yMin);
    context.strokeStyle = "rgba(255,255,255,0.08)";
    context.beginPath();
    context.moveTo(left, y);
    context.lineTo(width - 18, y);
    context.stroke();
    context.fillText(value.toFixed(2), 8, y + 4);
  }

  xLabels.forEach(({ x, label }) => {
    context.strokeStyle = "rgba(255,255,255,0.08)";
    context.beginPath();
    context.moveTo(x, 18);
    context.lineTo(x, bottom);
    context.stroke();
    context.fillText(label, x - 18, height - 14);
  });
}

function linePoint(index, value, length, width, height, min, max) {
  return {
    x: 62 + (index / (length - 1)) * (width - 82),
    y: 18 + ((max - value) / (max - min || 1)) * (height - 58),
  };
}

function drawLine(context, values, width, height, min, max, color, widthLine = 2) {
  context.strokeStyle = color;
  context.lineWidth = widthLine;
  context.beginPath();
  values.forEach((value, index) => {
    const point = linePoint(index, value, values.length, width, height, min, max);
    index === 0 ? context.moveTo(point.x, point.y) : context.lineTo(point.x, point.y);
  });
  context.stroke();
}

function drawLineChart(canvas, labels, series) {
  const { context, width, height } = setupCanvas(canvas);
  context.clearRect(0, 0, width, height);
  const allValues = series.flatMap((item) => item.values);
  const min = Math.min(...allValues, -1);
  const max = Math.max(...allValues, 1);
  const xTicks = Array.from({ length: 7 }, (_, tick) => {
    const index = Math.round((tick / 6) * (labels.length - 1));
    return { x: 62 + (index / (labels.length - 1)) * (width - 82), label: `${labels[index].toFixed(2)}с` };
  });
  drawAxes(context, width, height, xTicks, min, max);
  series.forEach((item, index) => drawLine(context, item.values, width, height, min, max, item.color || colors[index], item.width || 2));
  drawLegend(context, series, width);
}

function drawLegend(context, series, width) {
  let x = 76;
  const y = 30;
  series.forEach((item, index) => {
    context.fillStyle = item.color || colors[index];
    context.fillRect(x, y - 9, 18, 4);
    context.fillStyle = "#e5eefb";
    context.font = "12px sans-serif";
    context.fillText(item.name, x + 24, y - 4);
    x += Math.min(190, Math.max(110, item.name.length * 8 + 48));
    if (x > width - 160) x = 76;
  });
}

function logPosition(value, minFrequency, maxFrequency, width) {
  const safeValue = Math.max(value, minFrequency);
  const minLog = Math.log10(minFrequency);
  const maxLog = Math.log10(maxFrequency);
  return 62 + ((Math.log10(safeValue) - minLog) / (maxLog - minLog || 1)) * (width - 92);
}

function drawSpectrum(canvas, points, color) {
  const { context, width, height } = setupCanvas(canvas);
  context.clearRect(0, 0, width, height);
  const positive = points.filter((point) => point.frequency > 0);
  const maxFrequency = Math.max(...positive.map((point) => point.frequency), 10);
  const minFrequency = Math.max(Math.min(...positive.map((point) => point.frequency), 1), 0.1);
  const maxAmplitude = Math.max(...positive.map((point) => point.amplitude), 1);
  const tickValues = [minFrequency, minFrequency * 2, minFrequency * 5, maxFrequency / 2, maxFrequency].filter((value, index, array) => value <= maxFrequency && array.indexOf(value) === index);
  const xTicks = tickValues.map((value) => ({ x: logPosition(value, minFrequency, maxFrequency, width), label: `${value.toFixed(1)}Гц` }));
  drawAxes(context, width, height, xTicks, 0, maxAmplitude);
  positive.forEach((point) => {
    const x = logPosition(point.frequency, minFrequency, maxFrequency, width);
    const barHeight = (point.amplitude / maxAmplitude) * (height - 68);
    context.fillStyle = color;
    context.fillRect(x - 7, height - 40 - barHeight, 14, barHeight);
    context.fillStyle = "#9fb0c7";
    context.font = "12px sans-serif";
    context.fillText(`${point.frequency}Гц`, Math.max(64, x - 22), height - 14);
  });
}

function renderCharts() {
  const data = state.visualization;
  if (!data) return;
  const signalSeries = [
    { name: "Сумма гармоник", values: data.signal, color: colors[0], width: 3 },
    ...data.standaloneSignals.map((signal, index) => ({ name: signal.name, values: signal.points, color: colors[index + 1], width: 2 })),
  ];
  drawLineChart(canvases.signal, data.time, signalSeries);
  drawSpectrum(canvases.spectrum, data.spectrum, "#a78bfa");
  drawSpectrum(canvases.pure, data.pureSpectrum, "#34d399");
  drawSpectrum(canvases.filtered, data.filteredSpectrum, "#fbbf24");
  document.getElementById("filter-info").textContent = `Порог низкочастотного фильтра: ${data.cutoffFrequency} Гц. Шкала X логарифмическая.`;
}

function setupHoverInfo() {
  Object.values(canvases).forEach((canvas) => {
    canvas.addEventListener("mousemove", (event) => {
      const rect = canvas.getBoundingClientRect();
      const xPercent = Math.max(0, Math.min(1, (event.clientX - rect.left - 62) / Math.max(1, rect.width - 82)));
      document.getElementById("hover-info").textContent = `Позиция курсора на графике: ${(xPercent * 100).toFixed(1)}% ширины`;
    });
  });
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

document.getElementById("apply-preview").addEventListener("click", () => applyPreview().catch((error) => setMessage(error.message)));
document.getElementById("reset-form").addEventListener("click", () => fillForm(null));
setupSliderSync();
setupHoverInfo();
window.addEventListener("resize", renderCharts);
loadData().catch((error) => setMessage(error.message));
