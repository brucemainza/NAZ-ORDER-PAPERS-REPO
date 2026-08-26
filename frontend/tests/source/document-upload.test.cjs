const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("submission form supports drag-and-drop document upload", () => {
  const form = readFileSync(
    join(projectRoot, "src/components/submit/SubmitForm.jsx"),
    "utf8",
  );
  const hook = readFileSync(
    join(projectRoot, "src/hooks/useDocumentUpload.js"),
    "utf8",
  );
  const route = readFileSync(
    join(projectRoot, "src/app/api/submissions/upload/route.js"),
    "utf8",
  );

  assert.match(form, /onDrop/);
  assert.match(form, /onDragOver/);
  assert.match(form, /type="file"/);
  assert.match(form, /application\/pdf/);
  assert.match(form, /useDocumentUpload/);
  assert.match(hook, /\/api\/submissions\/upload/);
  assert.match(hook, /\.pdf/);
  assert.match(hook, /\.docx/);
  assert.match(hook, /\.txt/);
  assert.match(route, /\/submissions\/upload/);
  assert.match(route, /body:\s*request\.body/);
  assert.doesNotMatch(route, /request\.formData/);
});
