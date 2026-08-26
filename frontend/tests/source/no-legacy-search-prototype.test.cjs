const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("the retired client-side search prototype is not shipped", () => {
  assert.equal(existsSync(join(projectRoot, "src/hooks/useSearch.js")), false);

  const mockData = readFileSync(
    join(projectRoot, "src/lib/mockData.js"),
    "utf8",
  );
  for (const obsoleteSymbol of [
    "mockSubmissions",
    "mockSimilarityResults",
    "mockDecisionHistory",
    "mockAuditLogs",
    "searchHistoricalRecords",
    "buildSimilarityResultsForSubmission",
  ]) {
    assert.doesNotMatch(mockData, new RegExp(`\\b${obsoleteSymbol}\\b`));
  }
});
