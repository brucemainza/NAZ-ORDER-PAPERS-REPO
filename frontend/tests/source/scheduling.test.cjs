const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("result page schedules approved items through a frontend proxy", () => {
  const page = readFileSync(
    join(projectRoot, "src/app/(dashboard)/results/[id]/page.jsx"),
    "utf8",
  );
  const routePath = join(
    projectRoot,
    "src/app/api/submissions/[id]/schedule/route.js",
  );

  assert.match(page, /hasPermission\(user,\s*"schedule_item"\)/);
  assert.match(page, /Sitting Date/);
  assert.equal(existsSync(routePath), true);
});
