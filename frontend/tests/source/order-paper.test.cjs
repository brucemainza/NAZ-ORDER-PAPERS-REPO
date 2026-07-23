const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("frontend proxies generated Order Papers by sitting date", () => {
  const routePath = join(
    projectRoot,
    "src/app/api/order-papers/[date]/route.js",
  );

  assert.equal(existsSync(routePath), true);
  const route = readFileSync(routePath, "utf8");
  assert.match(route, /order-papers/);
});
