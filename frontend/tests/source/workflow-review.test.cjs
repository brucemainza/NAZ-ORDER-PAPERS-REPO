const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("result page exposes permission-aware workflow actions", () => {
  const page = readFileSync(
    join(projectRoot, "src/app/(dashboard)/results/[id]/page.jsx"),
    "utf8",
  );

  assert.match(page, /hasPermission\(user,\s*"approve_motion"\)/);
  assert.match(page, /hasPermission\(user,\s*"reject_submission"\)/);
  assert.match(page, /hasPermission\(user,\s*"request_changes"\)/);
  assert.match(page, /Request Changes/);
});

test("frontend proxies workflow review actions", () => {
  const routePath = join(
    projectRoot,
    "src/app/api/submissions/[id]/workflow-review/route.js",
  );

  assert.equal(existsSync(routePath), true);
  const route = readFileSync(routePath, "utf8");
  assert.match(route, /workflow-review/);
});
