const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("backend proxy formats structured validation errors for users", () => {
  const proxy = readFileSync(
    join(projectRoot, "src/lib/backendProxy.js"),
    "utf8",
  );

  assert.match(proxy, /Array\.isArray\(data\.detail\)/);
  assert.match(proxy, /error\.loc/);
  assert.match(proxy, /error\.msg/);
});
