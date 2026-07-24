const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("submission form exposes item types from permissions", () => {
  const page = readFileSync(
    join(projectRoot, "src/app/(dashboard)/submit/page.jsx"),
    "utf8",
  );

  assert.match(page, /hasPermission\(user,\s*"submit_question"\)/);
  assert.match(page, /hasPermission\(user,\s*"submit_motion"\)/);
  assert.doesNotMatch(page, /user[^;\n]*\.role\s*(?:===|!==)/);
});
