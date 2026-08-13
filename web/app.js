"use strict";

const core = globalThis.UVSpectrumCore;
const MAX_FILES = 12;
const MAX_BYTES = 5 * 1024 * 1024;
const palette = ["#0b7a70", "#7367c4", "#d47a32", "#b54f79", "#3376b8", "#70933d", "#b06337", "#468c84", "#8e62a8", "#526ba8", "#9b7438", "#b35656"];
const state = { docs: [], activeId: null, drag: null, batchSummary: [], drawFrame: 0 };
const $ = (selector) => document.querySelector(selector);

function uid() { return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`; }
function activeDoc() { return state.docs.find((doc) => doc.id === state.activeId) || null; }
function overlayDocs() { const selected = state.docs.filter((doc) => doc.compareEnabled); return selected.length ? selected : (activeDoc() ? [activeDoc()] : []); }
function escapeHtml(text) { const element = document.createElement("span"); element.textContent = String(text ?? ""); return element.innerHTML; }
function nice(value, digits = 5) { const number = Number(value); if (!Number.isFinite(number)) return "—"; const magnitude = Math.abs(number); return magnitude !== 0 && (magnitude >= 10000 || magnitude < 0.001) ? number.toExponential(3) : number.toFixed(digits).replace(/\.?0+$/, ""); }
function setMessage(text = "", kind = "error") { const element = $("#message"); element.textContent = text; element.dataset.kind = kind; element.hidden = !text; }

async function addFiles(files) {
  setMessage();
  const list = [...files];
  const remaining = MAX_FILES - state.docs.length;
  if (list.length > remaining) setMessage(`只添加前 ${remaining} 个文件；最多同时管理 ${MAX_FILES} 个。`, "warning");
  for (const file of list.slice(0, remaining)) {
    try {
      if (file.size > MAX_BYTES) throw new Error(`${file.name} 超过 5 MB。`);
      const data = core.parseSpectrum(await file.text());
      const span = data.x[data.x.length - 1] - data.x[0];
      const selection = { lo: data.x[0] + span * 0.35, hi: data.x[0] + span * 0.65 };
      state.docs.push({ id: uid(), name: file.name, ...data, compareEnabled: true, color: palette[state.docs.length % palette.length], selection, result: null, records: [], baselineId: null, view: null });
    } catch (error) { setMessage(error.message); }
  }
  if (!state.activeId && state.docs.length) state.activeId = state.docs[0].id;
  $("#fileInput").value = "";
  syncSelectionInputs();
  resetView(false);
  render();
}

const dropzone = $("#dropzone");
$("#fileInput").addEventListener("change", (event) => addFiles(event.target.files));
["dragenter", "dragover"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

$("#fileList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-id]");
  if (!row) return;
  const id = row.dataset.id;
  if (event.target.closest("[data-remove]")) {
    state.docs = state.docs.filter((doc) => doc.id !== id);
    if (state.activeId === id) state.activeId = state.docs[0]?.id || null;
    state.batchSummary = [];
    syncSelectionInputs();
    resetView(false);
  } else if (!event.target.matches("input[type=checkbox]")) {
    saveViewInputs();
    state.activeId = id;
    syncSelectionInputs();
    syncViewInputs();
  }
  render();
});

$("#fileList").addEventListener("change", (event) => {
  if (!event.target.matches("input[type=checkbox]")) return;
  const doc = state.docs.find((item) => item.id === event.target.closest("[data-id]")?.dataset.id);
  if (doc) doc.compareEnabled = event.target.checked;
  resetView(false);
  render();
});

$("#selectAllButton").addEventListener("click", () => { state.docs.forEach((doc) => { doc.compareEnabled = true; }); resetView(false); render(); });
$("#clearSelectionButton").addEventListener("click", () => { state.docs.forEach((doc) => { doc.compareEnabled = doc.id === state.activeId; }); resetView(false); render(); });
$("#clearFilesButton").addEventListener("click", () => { state.docs = []; state.activeId = null; state.batchSummary = []; render(); });

function syncSelectionInputs() {
  const doc = activeDoc();
  if (!doc) { $("#rangeMin").value = ""; $("#rangeMax").value = ""; return; }
  $("#rangeMin").value = Number(doc.selection.lo.toPrecision(9));
  $("#rangeMax").value = Number(doc.selection.hi.toPrecision(9));
}

function selectionValues() {
  const lo = Number($("#rangeMin").value);
  const hi = Number($("#rangeMax").value);
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) throw new Error("请输入有效的积分范围。");
  return lo < hi ? [lo, hi] : [hi, lo];
}

function calculateFor(doc, lo, hi) {
  const result = core.computeArea(doc.x, doc.y, lo, hi);
  doc.selection = { lo: result.lo, hi: result.hi };
  doc.result = result;
  return result;
}

function calculateCurrent() {
  const doc = activeDoc();
  if (!doc) return;
  try {
    const [lo, hi] = selectionValues();
    calculateFor(doc, lo, hi);
    syncSelectionInputs();
    setMessage();
    render();
  } catch (error) { setMessage(error.message); }
}

$("#calculateButton").addEventListener("click", calculateCurrent);
$("#batchButton").addEventListener("click", () => {
  if (!state.docs.length) return;
  try {
    const [lo, hi] = selectionValues();
    const rows = [];
    let referenceArea = null;
    for (const [index, doc] of state.docs.entries()) {
      const result = calculateFor(doc, lo, hi);
      const record = createRecord(doc, result, `批量峰${doc.records.length + 1}`, "batch");
      doc.records.push(record);
      if (!doc.baselineId) doc.baselineId = record.id;
      if (index === 0) referenceArea = record.correctedArea;
      rows.push({ docId: doc.id, file: doc.name, record, ratio: referenceArea && Math.abs(referenceArea) > 1e-12 ? record.correctedArea / referenceArea * 100 : null });
    }
    state.batchSummary = rows;
    setMessage(`已按 ${nice(lo, 3)}–${nice(hi, 3)} nm 完成 ${rows.length} 个文件的批量积分。`, "success");
    render();
  } catch (error) { setMessage(error.message); }
});

function createRecord(doc, result, name, source) {
  return { id: uid(), docId: doc.id, file: doc.name, name, lo: result.lo, hi: result.hi, rawArea: result.rawArea, baselineArea: result.baselineArea, correctedArea: result.correctedArea, positiveArea: result.positiveArea, points: result.points, source };
}

$("#recordButton").addEventListener("click", () => {
  const doc = activeDoc();
  if (!doc?.result) return;
  const record = createRecord(doc, doc.result, `峰${doc.records.length + 1}`, "manual");
  doc.records.push(record);
  if (!doc.baselineId) doc.baselineId = record.id;
  state.batchSummary = [];
  setMessage(`${doc.name} 已记录 ${record.name}。`, "success");
  render();
});

$("#baselineSelect").addEventListener("change", (event) => { const doc = activeDoc(); if (doc) doc.baselineId = event.target.value; renderRecords(); });

$("#recordRows").addEventListener("change", (event) => {
  if (!event.target.matches("[data-name]")) return;
  const doc = state.docs.find((item) => item.id === event.target.dataset.doc);
  const record = doc?.records.find((item) => item.id === event.target.dataset.name);
  if (record) record.name = event.target.value.trim() || record.name;
  renderRecords();
});

$("#recordRows").addEventListener("click", (event) => {
  const button = event.target.closest("[data-delete]");
  if (!button) return;
  const doc = state.docs.find((item) => item.id === button.dataset.doc);
  if (!doc) return;
  doc.records = doc.records.filter((record) => record.id !== button.dataset.delete);
  if (!doc.records.some((record) => record.id === doc.baselineId)) doc.baselineId = doc.records[0]?.id || null;
  state.batchSummary = [];
  renderRecords();
});

function baselineRecord(doc) { return doc.records.find((record) => record.id === doc.baselineId) || doc.records[0] || null; }
function recordRatio(doc, record) { const baseline = baselineRecord(doc); return !baseline || Math.abs(baseline.correctedArea) <= 1e-12 ? null : record.correctedArea / baseline.correctedArea * 100; }

function allRecords() { return state.docs.flatMap((doc) => doc.records.map((record) => ({ doc, record }))); }

function renderFiles() {
  $("#fileCount").textContent = `${state.docs.length} / ${MAX_FILES} FILES`;
  const list = $("#fileList");
  if (!state.docs.length) { list.innerHTML = "<p>尚未加载文件</p>"; return; }
  list.innerHTML = state.docs.map((doc) => `<div class="file-item ${doc.id === state.activeId ? "active" : ""}" data-id="${doc.id}"><label class="visibility" title="加入叠加"><input type="checkbox" ${doc.compareEnabled ? "checked" : ""}/><i style="--curve:${doc.color}"></i></label><button class="file-name"><b>${escapeHtml(doc.name)}</b><small>${doc.x.length.toLocaleString()} 点 · ${nice(doc.x[0], 2)}–${nice(doc.x[doc.x.length - 1], 2)} nm · ${doc.records.length} 峰</small></button><button class="remove" data-remove aria-label="移除">×</button></div>`).join("");
}

function renderCurrentResult() {
  const doc = activeDoc();
  const result = doc?.result;
  $("#currentResult").hidden = !result;
  $("#recordButton").disabled = !result;
  if (!result) return;
  $("#correctedArea").textContent = nice(result.correctedArea);
  $("#rawArea").textContent = nice(result.rawArea);
  $("#baselineArea").textContent = nice(result.baselineArea);
  $("#positiveArea").textContent = nice(result.positiveArea);
  $("#resultPoints").textContent = result.points.toLocaleString();
  $("#resultRange").textContent = `${nice(result.lo, 3)}–${nice(result.hi, 3)} nm`;
}

function renderRecords() {
  const entries = allRecords();
  $("#recordCount").textContent = `${entries.length} 条记录 / ${state.docs.length} 个文件`;
  $("#exportButton").disabled = !entries.length;
  const doc = activeDoc();
  const baselineSelect = $("#baselineSelect");
  baselineSelect.disabled = !doc?.records.length;
  baselineSelect.innerHTML = doc?.records.length ? doc.records.map((record) => `<option value="${record.id}" ${record.id === (doc.baselineId || doc.records[0].id) ? "selected" : ""}>${escapeHtml(record.name)}</option>`).join("") : '<option value="">无记录</option>';
  const body = $("#recordRows");
  if (!entries.length) { body.innerHTML = '<tr><td colspan="8">尚未记录峰；可记录当前积分或执行批量计算。</td></tr>'; }
  else body.innerHTML = entries.map(({ doc: itemDoc, record }) => `<tr class="${itemDoc.id === state.activeId ? "active-row" : ""}"><td><i class="file-dot" style="--curve:${itemDoc.color}"></i>${escapeHtml(itemDoc.name)}</td><td><input class="record-name" data-doc="${itemDoc.id}" data-name="${record.id}" value="${escapeHtml(record.name)}" aria-label="峰名称"/></td><td>${nice(record.lo, 3)}–${nice(record.hi, 3)}</td><td>${nice(record.correctedArea)}</td><td>${nice(record.positiveArea)}</td><td>${nice(recordRatio(itemDoc, record), 2)}${recordRatio(itemDoc, record) === null ? "" : "%"}</td><td><span class="source source-${record.source}">${record.source === "batch" ? "批量" : "手动"}</span></td><td><button class="delete-record" data-doc="${itemDoc.id}" data-delete="${record.id}">×</button></td></tr>`).join("");
  const strip = $("#summaryStrip");
  strip.hidden = !state.batchSummary.length;
  strip.innerHTML = state.batchSummary.length ? `<div><small>BATCH SUMMARY</small><strong>${state.batchSummary.length}</strong><span>文件</span></div><div><small>最大扣基线面积</small><strong>${nice(Math.max(...state.batchSummary.map((row) => row.record.correctedArea)))}</strong></div><div><small>最小扣基线面积</small><strong>${nice(Math.min(...state.batchSummary.map((row) => row.record.correctedArea)))}</strong></div><div><small>相对首文件</small><strong>${state.batchSummary.map((row) => nice(row.ratio, 1)).join(" / ")}%</strong></div>` : "";
}

function saveViewInputs() {
  const doc = activeDoc();
  if (!doc) return;
  const values = [$("#viewXMin"), $("#viewXMax"), $("#viewYMin"), $("#viewYMax")].map((input) => Number(input.value));
  if (values.every(Number.isFinite) && values[0] < values[1] && values[2] < values[3]) doc.view = { xMin: values[0], xMax: values[1], yMin: values[2], yMax: values[3] };
}

function syncViewInputs() {
  const doc = activeDoc();
  if (!doc) return;
  if (!doc.view) resetView(false);
  const view = doc.view;
  $("#viewXMin").value = Number(view.xMin.toPrecision(9)); $("#viewXMax").value = Number(view.xMax.toPrecision(9));
  $("#viewYMin").value = Number(view.yMin.toPrecision(9)); $("#viewYMax").value = Number(view.yMax.toPrecision(9));
}

function resetView(shouldRender = true) {
  const doc = activeDoc();
  if (!doc) return;
  try { doc.view = core.bounds(overlayDocs()); syncViewInputs(); if (shouldRender) scheduleDraw(); } catch (error) { setMessage(error.message); }
}

$("#resetViewButton").addEventListener("click", () => resetView(true));
$("#applyViewButton").addEventListener("click", () => {
  const doc = activeDoc(); if (!doc) return;
  const values = [$("#viewXMin"), $("#viewXMax"), $("#viewYMin"), $("#viewYMax")].map((input) => Number(input.value));
  if (!values.every(Number.isFinite) || values[0] >= values[1] || values[2] >= values[3]) return setMessage("视图最小值必须小于最大值，且四项都要填写。");
  doc.view = { xMin: values[0], xMax: values[1], yMin: values[2], yMax: values[3] };
  setMessage(); scheduleDraw();
});

function geometry() {
  const doc = activeDoc();
  if (!doc?.view) resetView(false);
  const view = doc.view;
  const W = 1120, H = 520, L = 72, R = 24, T = 24, B = 56;
  return { ...view, W, H, L, R, T, B, sx: (x) => L + (x - view.xMin) / (view.xMax - view.xMin || 1) * (W - L - R), sy: (y) => T + (view.yMax - y) / (view.yMax - view.yMin || 1) * (H - T - B), ux: (pixel) => view.xMin + (pixel - L) / (W - L - R) * (view.xMax - view.xMin), uy: (pixel) => view.yMax - (pixel - T) / (H - T - B) * (view.yMax - view.yMin) };
}

function scheduleDraw() { cancelAnimationFrame(state.drawFrame); state.drawFrame = requestAnimationFrame(drawChart); }

function drawChart() {
  const doc = activeDoc(); if (!doc) return;
  const g = geometry(); let html = "";
  for (let index = 0; index <= 5; index += 1) {
    const px = g.L + index / 5 * (g.W - g.L - g.R), xv = g.xMin + index / 5 * (g.xMax - g.xMin);
    const py = g.T + index / 5 * (g.H - g.T - g.B), yv = g.yMax - index / 5 * (g.yMax - g.yMin);
    html += `<line class="grid" x1="${px}" y1="${g.T}" x2="${px}" y2="${g.H-g.B}"/><text class="axis-label" x="${px}" y="${g.H-24}" text-anchor="middle">${nice(xv, 1)}</text><line class="grid" x1="${g.L}" y1="${py}" x2="${g.W-g.R}" y2="${py}"/><text class="axis-label" x="${g.L-9}" y="${py+4}" text-anchor="end">${nice(yv, 2)}</text>`;
  }
  const selection = state.drag ? { lo: Math.min(state.drag.startValue, state.drag.currentValue), hi: Math.max(state.drag.startValue, state.drag.currentValue), drag: true } : doc.selection;
  if (selection) {
    const x1 = Math.max(g.L, Math.min(g.W-g.R, g.sx(selection.lo))); const x2 = Math.max(g.L, Math.min(g.W-g.R, g.sx(selection.hi)));
    html += `<rect class="${selection.drag ? "drag-selection" : "selection"}" x="${Math.min(x1,x2)}" y="${g.T}" width="${Math.abs(x2-x1)}" height="${g.H-g.T-g.B}"/>`;
  }
  if (doc.result) html += `<path class="baseline" d="M${g.sx(doc.result.xs[0])},${g.sy(doc.result.baseline[0])} L${g.sx(doc.result.xs[doc.result.xs.length-1])},${g.sy(doc.result.baseline[doc.result.baseline.length-1])}"/>`;
  const shown = overlayDocs();
  for (const item of shown) {
    const curve = core.visibleCurve(item.x, item.y, g.xMin, g.xMax, 1800);
    const path = curve.x.map((x, index) => `${index ? "L" : "M"}${g.sx(x).toFixed(2)},${g.sy(curve.y[index]).toFixed(2)}`).join(" ");
    html += `<path class="spectrum ${item.id === state.activeId ? "active-spectrum" : ""}" style="stroke:${item.color}" d="${path}"/>`;
  }
  $("#chart").innerHTML = html;
  $("#chartLegend").innerHTML = shown.map((item) => `<span style="--curve:${item.color}"><i></i>${escapeHtml(item.name)}</span>`).join("");
}

const chart = $("#chart");
function svgPoint(event) { const rect = chart.getBoundingClientRect(); return { x: (event.clientX - rect.left) / rect.width * 1120, y: (event.clientY - rect.top) / rect.height * 520 }; }
chart.addEventListener("pointerdown", (event) => { if (!activeDoc() || event.button !== 0) return; const g = geometry(), point = svgPoint(event); if (point.x < g.L || point.x > g.W-g.R) return; const value = g.ux(point.x); state.drag = { pointerId: event.pointerId, startValue: value, currentValue: value }; chart.setPointerCapture(event.pointerId); scheduleDraw(); });
chart.addEventListener("pointermove", (event) => { if (!state.drag || event.pointerId !== state.drag.pointerId) return; const g = geometry(), point = svgPoint(event); state.drag.currentValue = g.ux(Math.max(g.L, Math.min(g.W-g.R, point.x))); scheduleDraw(); });
chart.addEventListener("pointerup", (event) => { if (!state.drag || event.pointerId !== state.drag.pointerId) return; const doc = activeDoc(), lo = Math.min(state.drag.startValue, state.drag.currentValue), hi = Math.max(state.drag.startValue, state.drag.currentValue), g = geometry(); state.drag = null; if (hi - lo < (g.xMax - g.xMin) * 0.003) return scheduleDraw(); doc.selection = { lo, hi }; syncSelectionInputs(); calculateCurrent(); });
chart.addEventListener("pointercancel", () => { state.drag = null; scheduleDraw(); });
chart.addEventListener("wheel", (event) => {
  const doc = activeDoc(); if (!doc) return;
  event.preventDefault();
  const g = geometry(), point = svgPoint(event), anchorX = g.ux(point.x), anchorY = g.uy(point.y), scale = event.deltaY < 0 ? 1 / 1.2 : 1.2;
  doc.view = { xMin: anchorX - (anchorX - g.xMin) * scale, xMax: anchorX + (g.xMax - anchorX) * scale, yMin: anchorY - (anchorY - g.yMin) * scale, yMax: anchorY + (g.yMax - anchorY) * scale };
  syncViewInputs(); scheduleDraw();
}, { passive: false });

function csvCell(value) { return `"${String(value ?? "").replaceAll('"', '""')}"`; }
$("#exportButton").addEventListener("click", () => {
  const rows = [["文件名", "峰名", "积分范围", "原始面积", "基线面积", "扣基线面积", "仅正面积", "数据点", "与基准比值", "来源"]];
  for (const { doc, record } of allRecords()) rows.push([doc.name, record.name, `${record.lo.toFixed(3)} - ${record.hi.toFixed(3)}`, record.rawArea, record.baselineArea, record.correctedArea, record.positiveArea, record.points, recordRatio(doc, record) === null ? "-" : `${recordRatio(doc, record).toFixed(2)}%`, record.source]);
  const csv = rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" })); link.download = "uv-spectrum-summary.csv"; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 0);
});

function updateButtons() {
  const hasDocs = state.docs.length > 0;
  $("#calculateButton").disabled = !hasDocs; $("#batchButton").disabled = !hasDocs; $("#selectAllButton").disabled = !hasDocs; $("#clearSelectionButton").disabled = !hasDocs; $("#clearFilesButton").disabled = !hasDocs;
}

function render() {
  renderFiles(); updateButtons(); renderCurrentResult(); renderRecords();
  const hasDocs = state.docs.length > 0;
  $("#empty").hidden = hasDocs; $("#analysis").hidden = !hasDocs;
  $("#activeLabel").textContent = activeDoc()?.name.toUpperCase() || "NO ACTIVE SPECTRUM";
  if (hasDocs) { syncViewInputs(); scheduleDraw(); }
}

render();
