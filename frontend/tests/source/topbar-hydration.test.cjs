const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("top bar exposes route, notifications, and account logout controls", () => {
  const topbar = readFileSync(
    join(projectRoot, "src/components/layout/Topbar.jsx"),
    "utf8",
  );

  assert.match(topbar, /usePathname/);
  assert.match(topbar, /href="\/notifications"/);
  assert.match(topbar, /aria-haspopup="menu"/);
  assert.match(topbar, /await logout\(\)/);
  assert.match(topbar, /router\.replace\("\/login"\)/);
  assert.doesNotMatch(topbar, /topbar__role/);
});
