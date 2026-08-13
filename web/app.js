"use strict";

const state = { docs: [], activeId: null, result: null, records: [], dragStart: null };
const palette = ["#146d58", "#735dde", "#ed865d", "#3185b8", "#9b6c31", "#c45180"];
const $ = (selector) => document.querySelector(selector);

function setMessage(text = "") { $("#message").textContent = text; $("#message").hidden = !text; }
function nice(value, digits = 5) { const n = Number(value); if (!Number.isFinite(n)) return "—"; const a = Math.abs(n); return a !== 0 && (a >= 10000 || a < 0.001) ? n.toExponential(3) : n.toFixed(digits).replace(/\.?0+$/, ""); }
function id() { return `${Date.now()}-${Math.random().toString(16).slice(2)}`; }

function parseSpectrum(text) {
  const rows = [];
  text.split(/\r?\n/).forEach((line) => {
    const parts = line.trim().replaceAll(";", " ").replaceAll(",", " ").split(/\s+/);
    if (parts.length < 2) return;
    const x = Number(parts[0]), y = Number(parts[1]);
    if (Number.isFinite(x) && Number.isFinite(y)) rows.push([x, y]);
  });
  if (rows.length < 2) throw new Error("未找到至少两行两列数值数据。");
  rows.sort((a, b) => a[0] - b[0]);
  const unique = rows.filter((row, index) => index === 0 || row[0] !== rows[index - 1][0]);
  return { x: unique.map((row) => row[0]), y: unique.map((row) => row[1]) };
}

async function addFiles(files) {
  setMessage();
  for (const file of [...files].slice(0, Math.max(0, 6 - state.docs.length))) {
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error(`${file.name} 超过 5 MB。`);
      const data = parseSpectrum(await file.text());
      state.docs.push({ id: id(), name: file.name, ...data, enabled: true });
    } catch (error) { setMessage(error.message); }
  }
  if (!state.activeId && state.docs.length) state.activeId = state.docs[0].id;
  syncRangeToActive(); render();
}

const dropzone = $("#dropzone");
$("#fileInput").addEventListener("change", (event) => addFiles(event.target.files));
["dragenter", "dragover"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

function activeDoc() { return state.docs.find((doc) => doc.id === state.activeId); }
function syncRangeToActive() {
  const doc = activeDoc(); if (!doc) return;
  const span = doc.x.at(-1) - doc.x[0];
  $("#rangeMin").value = Number((doc.x[0] + span * 0.35).toPrecision(7));
  $("#rangeMax").value = Number((doc.x[0] + span * 0.65).toPrecision(7));
}

function render() {
  renderFiles();
  const hasDocs = state.docs.length > 0;
  $("#empty").hidden = hasDocs; $("#analysis").hidden = !hasDocs; $("#calculateButton").disabled = !hasDocs;
  if (hasDocs) drawChart();
  renderRecords();
}

function renderFiles() {
  const list = $("#fileList");
  if (!state.docs.length) { list.innerHTML = "<p>尚未加载文件</p>"; return; }
  list.innerHTML = state.docs.map((doc, index) => `<div class="file-item ${doc.id === state.activeId ? "active" : ""}"><input type="checkbox" data-enable="${doc.id}" ${doc.enabled ? "checked" : ""}/><button data-active="${doc.id}"><b>${escapeHtml(doc.name)}</b><small>${doc.x.length.toLocaleString()} 点 · ${nice(doc.x[0],2)}–${nice(doc.x.at(-1),2)}</small></button><button class="remove" data-remove="${doc.id}" aria-label="移除">×</button></div>`).join("");
  list.querySelectorAll("[data-active]").forEach((button) => button.addEventListener("click", () => { state.activeId = button.dataset.active; state.result = null; syncRangeToActive(); render(); }));
  list.querySelectorAll("[data-enable]").forEach((input) => input.addEventListener("change", () => { state.docs.find((doc) => doc.id === input.dataset.enable).enabled = input.checked; drawChart(); }));
  list.querySelectorAll("[data-remove]").forEach((button) => button.addEventListener("click", () => { state.docs = state.docs.filter((doc) => doc.id !== button.dataset.remove); state.records = state.records.filter((row) => row.docId !== button.dataset.remove); if (!activeDoc()) state.activeId = state.docs[0]?.id || null; state.result = null; syncRangeToActive(); render(); }));
}

function extractSegment(x, y, lo, hi) {
  if (!(lo < hi)) throw new Error("积分起点必须小于终点。");
  if (hi < x[0] || lo > x.at(-1)) throw new Error("积分范围超出当前光谱边界。");
  lo = Math.max(lo, x[0]); hi = Math.min(hi, x.at(-1));
  const interp = (target) => { let i = 1; while (i < x.length && x[i] < target) i += 1; if (i >= x.length) return y.at(-1); const ratio = (target - x[i-1]) / (x[i] - x[i-1] || 1); return y[i-1] + ratio * (y[i] - y[i-1]); };
  const xs = [lo], ys = [interp(lo)];
  x.forEach((value, i) => { if (value > lo && value < hi) { xs.push(value); ys.push(y[i]); } });
  xs.push(hi); ys.push(interp(hi)); return { xs, ys };
}

function trapezoid(y, x) { let area = 0; for (let i = 1; i < x.length; i += 1) area += (y[i-1] + y[i]) * 0.5 * (x[i] - x[i-1]); return area; }
function compute(doc, lo, hi) {
  const { xs, ys } = extractSegment(doc.x, doc.y, lo, hi);
  const baseline = xs.map((x) => ys[0] + (ys.at(-1) - ys[0]) * (x - xs[0]) / (xs.at(-1) - xs[0]));
  const corrected = ys.map((y, i) => y - baseline[i]);
  return { docId: doc.id, file: doc.name, lo: xs[0], hi: xs.at(-1), xs, ys, baseline, rawArea: trapezoid(ys, xs), baselineArea: trapezoid(baseline, xs), correctedArea: trapezoid(corrected, xs), positiveArea: trapezoid(corrected.map((v) => Math.max(v, 0)), xs), points: xs.length };
}

$("#calculateButton").addEventListener("click", calculate);
function calculate() {
  try {
    state.result = compute(activeDoc(), Number($("#rangeMin").value), Number($("#rangeMax").value));
    $("#currentResult").hidden = false; $("#correctedArea").textContent = nice(state.result.correctedArea); $("#rawArea").textContent = nice(state.result.rawArea); $("#positiveArea").textContent = nice(state.result.positiveArea);
    $("#recordButton").disabled = false; setMessage(); drawChart();
  } catch (error) { setMessage(error.message); }
}

$("#recordButton").addEventListener("click", () => {
  if (!state.result) return;
  const sameDocCount = state.records.filter((row) => row.docId === state.result.docId).length;
  state.records.push({ ...state.result, id: id(), name: `峰 ${sameDocCount + 1}` });
  $("#exportButton").disabled = false; renderRecords();
});

function renderRecords() {
  const body = $("#recordRows"); $("#recordCount").textContent = `${state.records.length} 条记录`; $("#exportButton").disabled = !state.records.length;
  if (!state.records.length) { body.innerHTML = '<tr><td colspan="6">尚未记录峰</td></tr>'; return; }
  body.innerHTML = state.records.map((row) => `<tr><td>${escapeHtml(row.file)}</td><td>${row.name}</td><td>${nice(row.lo,3)}–${nice(row.hi,3)}</td><td>${nice(row.correctedArea)}</td><td>${nice(row.positiveArea)}</td><td><button class="delete-record" data-record="${row.id}">×</button></td></tr>`).join("");
  body.querySelectorAll("[data-record]").forEach((button) => button.addEventListener("click", () => { state.records = state.records.filter((row) => row.id !== button.dataset.record); renderRecords(); }));
}

function chartGeometry() {
  const docs = state.docs.filter((doc) => doc.enabled); const shown = docs.length ? docs : [activeDoc()];
  const xs = shown.flatMap((doc) => doc.x), ys = shown.flatMap((doc) => doc.y); const W=1040,H=500,L=70,R=22,T=20,B=52;
  const xMin=Math.min(...xs),xMax=Math.max(...xs),yRawMin=Math.min(...ys),yRawMax=Math.max(...ys),pad=Math.max((yRawMax-yRawMin)*.08,1e-9),yMin=yRawMin-pad,yMax=yRawMax+pad;
  return { shown,W,H,L,R,T,B,xMin,xMax,yMin,yMax,sx:(x)=>L+(x-xMin)/(xMax-xMin||1)*(W-L-R),sy:(y)=>T+(yMax-y)/(yMax-yMin||1)*(H-T-B),ux:(px)=>xMin+(px-L)/(W-L-R)*(xMax-xMin) };
}

function drawChart() {
  if (!state.docs.length) return; const g=chartGeometry(); let html="";
  for(let i=0;i<=5;i+=1){const px=g.L+i/5*(g.W-g.L-g.R),xv=g.xMin+i/5*(g.xMax-g.xMin),py=g.T+i/5*(g.H-g.T-g.B),yv=g.yMax-i/5*(g.yMax-g.yMin);html+=`<line class="grid" x1="${px}" y1="${g.T}" x2="${px}" y2="${g.H-g.B}"/><text class="axis-label" x="${px}" y="${g.H-23}" text-anchor="middle">${nice(xv,1)}</text><line class="grid" x1="${g.L}" y1="${py}" x2="${g.W-g.R}" y2="${py}"/><text class="axis-label" x="${g.L-9}" y="${py+4}" text-anchor="end">${nice(yv,2)}</text>`;}
  if(state.result){const x1=g.sx(state.result.lo),x2=g.sx(state.result.hi);html+=`<rect class="selection" x="${x1}" y="${g.T}" width="${x2-x1}" height="${g.H-g.T-g.B}"/><path class="baseline" d="M${g.sx(state.result.xs[0])},${g.sy(state.result.baseline[0])} L${g.sx(state.result.xs.at(-1))},${g.sy(state.result.baseline.at(-1))}"/>`;}
  g.shown.forEach((doc,index)=>{const d=doc.x.map((x,i)=>`${i?"L":"M"}${g.sx(x).toFixed(2)},${g.sy(doc.y[i]).toFixed(2)}`).join(" ");html+=`<path class="spectrum" style="stroke:${palette[index%palette.length]}" d="${d}"/>`;}); $("#chart").innerHTML=html;
}

const chart=$("#chart");
function eventX(event){const rect=chart.getBoundingClientRect();return (event.clientX-rect.left)/rect.width*1040;}
chart.addEventListener("pointerdown",(event)=>{if(!state.docs.length)return;state.dragStart=eventX(event);chart.setPointerCapture(event.pointerId);});
chart.addEventListener("pointerup",(event)=>{if(state.dragStart===null)return;const g=chartGeometry(),end=eventX(event),lo=g.ux(Math.max(g.L,Math.min(state.dragStart,end))),hi=g.ux(Math.min(g.W-g.R,Math.max(state.dragStart,end)));state.dragStart=null;if(Math.abs(hi-lo)<(g.xMax-g.xMin)*.005)return;$("#rangeMin").value=Number(lo.toPrecision(7));$("#rangeMax").value=Number(hi.toPrecision(7));calculate();});

$("#exportButton").addEventListener("click",()=>{const rows=[["file","peak","xmin","xmax","raw_area","baseline_area","corrected_area","positive_area","points"],...state.records.map((r)=>[r.file,r.name,r.lo,r.hi,r.rawArea,r.baselineArea,r.correctedArea,r.positiveArea,r.points])];const csv=rows.map((row)=>row.map((cell)=>`"${String(cell).replaceAll('"','""')}"`).join(",")).join("\r\n");const link=document.createElement("a");link.href=URL.createObjectURL(new Blob(["\ufeff",csv],{type:"text/csv"}));link.download="uv-spectrum-summary.csv";link.click();URL.revokeObjectURL(link.href);});
function escapeHtml(text){const el=document.createElement("span");el.textContent=text;return el.innerHTML;}
