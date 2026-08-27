const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("submission status filter exposes exactly the supported lifecycle values", () => {
  const searchBar = readFileSync(
    join(projectRoot, "src/components/search/SearchBar.jsx"),
    "utf8",
  );
  const statusSelect = searchBar
    .split('id="searchStatus"')[1]
    .split("</Select>")[0];
  const optionValues = [
    ...statusSelect.matchAll(/<option value="([^"]+)">/g),
  ].map((match) => match[1]);

  assert.deepEqual(optionValues, [
    "All",
    "Draft",
    "Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "Scheduled",
    "Archived",
  ]);
});
