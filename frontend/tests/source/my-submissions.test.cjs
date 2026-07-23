const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("frontend exposes the authenticated user's submissions API", () => {
  const routePath = join(
    projectRoot,
    "src/app/api/submissions/mine/route.js",
  );

  assert.equal(existsSync(routePath), true);
  const route = readFileSync(routePath, "utf8");
  assert.match(route, /proxyJson\("\/submissions\/mine"\)/);
});
