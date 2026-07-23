const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("search UI exposes and forwards date, member, and ministry filters", () => {
  const searchBar = readFileSync(
    join(projectRoot, "src/components/search/SearchBar.jsx"),
    "utf8",
  );
  const searchPage = readFileSync(
    join(projectRoot, "src/app/(dashboard)/search/page.jsx"),
    "utf8",
  );

  for (const filter of ["date", "member", "ministry"]) {
    assert.match(searchBar, new RegExp(filter, "i"));
    assert.match(searchPage, new RegExp(`params\\.append\\(\"${filter}\"`));
  }
});
