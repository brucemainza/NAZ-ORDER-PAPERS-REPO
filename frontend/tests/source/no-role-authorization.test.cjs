const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();
const authorizationFiles = [
  "src/lib/auth.js",
  "src/components/layout/Sidebar.jsx",
  "src/app/(dashboard)/sessions/page.jsx",
  "src/app/(dashboard)/users/page.jsx",
];

test("frontend authorization checks permissions rather than role names", () => {
  for (const file of authorizationFiles) {
    const source = readFileSync(join(projectRoot, file), "utf8");

    assert.doesNotMatch(source, /hasAdminAccess|adminOnly/);
    assert.doesNotMatch(source, /user[^;\n]*\.role\s*(?:===|!==)/);
  }
});
