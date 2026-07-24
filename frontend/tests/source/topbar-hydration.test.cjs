const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("top bar defers the current date until after client hydration", () => {
  const topbar = readFileSync(
    join(projectRoot, "src/components/layout/Topbar.jsx"),
    "utf8",
  );

  assert.match(topbar, /useEffect/);
  assert.match(topbar, /useState/);
  assert.match(topbar, /setCurrentDate/);
  assert.match(topbar, /\{currentDate\}/);
});
