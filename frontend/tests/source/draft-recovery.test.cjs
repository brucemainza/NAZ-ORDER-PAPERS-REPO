const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("frontend proxies draft edits and resubmission", () => {
  const routePath = join(
    projectRoot,
    "src/app/api/submissions/[id]/route.js",
  );
  const submitRoutePath = join(
    projectRoot,
    "src/app/api/submissions/[id]/submit/route.js",
  );

  assert.equal(existsSync(routePath), true);
  assert.equal(existsSync(submitRoutePath), true);

  const route = readFileSync(routePath, "utf8");
  const submitRoute = readFileSync(submitRoutePath, "utf8");
  assert.match(route, /export async function PATCH/);
  assert.match(submitRoute, /\/submit/);
});
