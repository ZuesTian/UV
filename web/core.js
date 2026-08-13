"use strict";

(function exposeUVSpectrumCore(root) {
  function parseSpectrum(text) {
    const rows = [];
    for (const line of String(text).split(/\r?\n/)) {
      const clean = line.trim();
      if (!clean || clean.startsWith("#")) continue;
      const parts = clean.replaceAll(";", " ").replaceAll(",", " ").split(/\s+/);
      if (parts.length < 2) continue;
      const x = Number(parts[0]);
      const y = Number(parts[1]);
      if (Number.isFinite(x) && Number.isFinite(y)) rows.push([x, y]);
    }
    if (rows.length < 2) throw new Error("未找到至少两行两列数值数据。");
    rows.sort((left, right) => left[0] - right[0]);
    const x = [];
    const y = [];
    for (const row of rows) {
      if (x.length && row[0] === x[x.length - 1]) continue;
      x.push(row[0]);
      y.push(row[1]);
    }
    if (x.length < 2) throw new Error("第一列至少需要两个不同的数值。");
    return { x, y };
  }

  function lowerBound(values, target) {
    let low = 0;
    let high = values.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (values[middle] < target) low = middle + 1;
      else high = middle;
    }
    return low;
  }

  function interpolate(x, y, target) {
    const right = lowerBound(x, target);
    if (right <= 0) return y[0];
    if (right >= x.length) return y[y.length - 1];
    if (x[right] === target) return y[right];
    const left = right - 1;
    const ratio = (target - x[left]) / (x[right] - x[left]);
    return y[left] + ratio * (y[right] - y[left]);
  }

  function extractSegment(x, y, minimum, maximum) {
    if (!Array.isArray(x) || !Array.isArray(y) || x.length !== y.length || x.length < 2) {
      throw new Error("光谱数据格式不正确。");
    }
    if (!(minimum < maximum)) throw new Error("范围最小值必须小于最大值。");
    if (maximum < x[0] || minimum > x[x.length - 1]) throw new Error("所选范围超出数据边界。");
    const lo = Math.max(minimum, x[0]);
    const hi = Math.min(maximum, x[x.length - 1]);
    const start = lowerBound(x, lo);
    const end = lowerBound(x, hi);
    const xs = [lo];
    const ys = [interpolate(x, y, lo)];
    for (let index = start; index < end; index += 1) {
      if (x[index] > lo && x[index] < hi) {
        xs.push(x[index]);
        ys.push(y[index]);
      }
    }
    if (hi > lo) {
      xs.push(hi);
      ys.push(interpolate(x, y, hi));
    }
    return { xs, ys };
  }

  function trapezoid(y, x) {
    let area = 0;
    for (let index = 1; index < x.length; index += 1) {
      area += (y[index - 1] + y[index]) * 0.5 * (x[index] - x[index - 1]);
    }
    return area;
  }

  function computeArea(x, y, minimum, maximum) {
    const { xs, ys } = extractSegment(x, y, minimum, maximum);
    const width = xs[xs.length - 1] - xs[0];
    const baseline = xs.map((value) => ys[0] + (ys[ys.length - 1] - ys[0]) * (value - xs[0]) / width);
    const corrected = ys.map((value, index) => value - baseline[index]);
    return {
      xs,
      ys,
      baseline,
      corrected,
      rawArea: trapezoid(ys, xs),
      baselineArea: trapezoid(baseline, xs),
      correctedArea: trapezoid(corrected, xs),
      positiveArea: trapezoid(corrected.map((value) => Math.max(value, 0)), xs),
      points: xs.length,
      lo: xs[0],
      hi: xs[xs.length - 1],
    };
  }

  function minMaxDownsample(x, y, maximum = 1800) {
    if (x.length <= maximum || maximum < 4) return { x: x.slice(), y: y.slice() };
    const bucketCount = Math.max(1, Math.floor((maximum - 2) / 2));
    const bucketSize = (x.length - 2) / bucketCount;
    const outputX = [x[0]];
    const outputY = [y[0]];
    for (let bucket = 0; bucket < bucketCount; bucket += 1) {
      const start = 1 + Math.floor(bucket * bucketSize);
      const end = Math.min(x.length - 1, 1 + Math.floor((bucket + 1) * bucketSize));
      if (start >= end) continue;
      let minIndex = start;
      let maxIndex = start;
      for (let index = start + 1; index < end; index += 1) {
        if (y[index] < y[minIndex]) minIndex = index;
        if (y[index] > y[maxIndex]) maxIndex = index;
      }
      const first = Math.min(minIndex, maxIndex);
      const second = Math.max(minIndex, maxIndex);
      outputX.push(x[first]); outputY.push(y[first]);
      if (second !== first) { outputX.push(x[second]); outputY.push(y[second]); }
    }
    outputX.push(x[x.length - 1]);
    outputY.push(y[y.length - 1]);
    return { x: outputX, y: outputY };
  }

  function visibleCurve(x, y, minimum, maximum, limit = 1800) {
    const start = Math.max(0, lowerBound(x, minimum) - 1);
    const end = Math.min(x.length, lowerBound(x, maximum) + 1);
    return minMaxDownsample(x.slice(start, end), y.slice(start, end), limit);
  }

  function bounds(documents) {
    let xMin = Infinity;
    let xMax = -Infinity;
    let yMin = Infinity;
    let yMax = -Infinity;
    for (const document of documents) {
      if (!document?.x?.length) continue;
      xMin = Math.min(xMin, document.x[0]);
      xMax = Math.max(xMax, document.x[document.x.length - 1]);
      for (const value of document.y) {
        if (!Number.isFinite(value)) continue;
        yMin = Math.min(yMin, value);
        yMax = Math.max(yMax, value);
      }
    }
    if (![xMin, xMax, yMin, yMax].every(Number.isFinite)) throw new Error("没有可绘制的光谱数据。");
    const padding = Math.max((yMax - yMin) * 0.08, 1e-9);
    return { xMin, xMax, yMin: yMin - padding, yMax: yMax + padding };
  }

  const api = { parseSpectrum, lowerBound, interpolate, extractSegment, trapezoid, computeArea, minMaxDownsample, visibleCurve, bounds };
  root.UVSpectrumCore = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis === "undefined" ? this : globalThis);
