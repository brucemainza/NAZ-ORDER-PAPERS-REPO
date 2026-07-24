const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("question submission captures and sends the oral or written answer type", () => {
  const form = readFileSync(
    join(projectRoot, "src/components/submit/SubmitForm.jsx"),
    "utf8",
  );
  const hook = readFileSync(
    join(projectRoot, "src/hooks/useSubmit.js"),
    "utf8",
  );

  assert.match(form, /answerType/);
  assert.match(form, /Oral/);
  assert.match(form, /Written/);
  assert.match(hook, /answer_type:\s*values\.answerType/);
});
