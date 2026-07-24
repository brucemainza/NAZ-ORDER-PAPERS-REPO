const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("authenticated visual baselines use a fixed browser clock", () => {
  const visualSpec = readFileSync(
    join(projectRoot, "tests/e2e/visual-baseline.spec.js"),
    "utf8",
  );

  assert.match(visualSpec, /page\.clock\.setFixedTime/);
  assert.match(visualSpec, /SNAPSHOT_TIME/);
});
