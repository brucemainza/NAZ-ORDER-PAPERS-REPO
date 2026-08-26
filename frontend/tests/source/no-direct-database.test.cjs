const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("frontend accesses PostgreSQL only through the backend API", () => {
  const packageJson = JSON.parse(
    readFileSync(join(projectRoot, "package.json"), "utf8"),
  );
  const dependencies = {
    ...packageJson.dependencies,
    ...packageJson.devDependencies,
  };

  assert.equal(dependencies.pg, undefined);
  assert.equal(existsSync(join(projectRoot, "src/lib/db.js")), false);
});

test("empty JavaScript type placeholders are not retained as source modules", () => {
  for (const filename of ["auth.js", "search.js", "submission.js"]) {
    assert.equal(existsSync(join(projectRoot, "src/types", filename)), false);
  }
});
