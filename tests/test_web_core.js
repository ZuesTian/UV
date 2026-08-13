"use strict";

const assert = require("node:assert/strict");
const core = require("../web/core.js");

const parsed = core.parseSpectrum("wavelength,absorbance\n3,9\n1,1\n2,4\n2,8\n");
assert.deepEqual(parsed.x, [1, 2, 3]);
assert.deepEqual(parsed.y, [1, 4, 9]);

const triangle = core.computeArea([0, 1, 2], [0, 1, 0], 0, 2);
assert.equal(triangle.rawArea, 1);
assert.equal(triangle.baselineArea, 0);
assert.equal(triangle.correctedArea, 1);
assert.equal(triangle.positiveArea, 1);
assert.equal(triangle.points, 3);

const clipped = core.computeArea([0, 1, 2], [0, 2, 0], 0.5, 1.5);
assert.deepEqual(clipped.xs, [0.5, 1, 1.5]);
assert.deepEqual(clipped.ys, [1, 2, 1]);
assert.equal(clipped.correctedArea, 0.5);

const x = Array.from({ length: 10000 }, (_, index) => index);
const y = x.map((value) => value === 4321 ? 1000 : Math.sin(value / 20));
const compact = core.minMaxDownsample(x, y, 500);
assert.ok(compact.x.length <= 500);
assert.equal(Math.max(...compact.y), 1000);

assert.equal(core.lowerBound([1, 3, 5, 7], 5), 2);
assert.equal(core.lowerBound([1, 3, 5, 7], 4), 2);
console.log("UV web core: all assertions passed");
