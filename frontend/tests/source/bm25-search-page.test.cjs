const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("keyword searches use BM25 and expose matching content context", () => {
  const searchPage = readFileSync(
    join(projectRoot, "src/app/(dashboard)/search/page.jsx"),
    "utf8",
  );
  const submissionCard = readFileSync(
    join(projectRoot, "src/components/submit/SubmissionCard.jsx"),
    "utf8",
  );

  assert.match(searchPage, /fetch\(\"\/api\/search\"/);
  assert.match(searchPage, /query_text/);
  assert.match(searchPage, /total_results/);
  assert.match(searchPage, /matched_terms/);
  assert.match(submissionCard, /matched_terms/);
  assert.match(submissionCard, /search_score/);
  assert.match(submissionCard, /full_text/);
});
