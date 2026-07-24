const assert = require("node:assert/strict");
const { existsSync, readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");

const projectRoot = process.cwd();

test("frontend has no Tailwind runtime or build-time dependency", () => {
  const packageJson = JSON.parse(
    readFileSync(join(projectRoot, "package.json"), "utf8"),
  );
  const dependencies = {
    ...packageJson.dependencies,
    ...packageJson.devDependencies,
  };

  assert.equal(dependencies.tailwindcss, undefined);
  assert.equal(dependencies["tailwind-merge"], undefined);
  assert.equal(existsSync(join(projectRoot, "tailwind.config.js")), false);

  const postcss = readFileSync(join(projectRoot, "postcss.config.js"), "utf8");
  assert.doesNotMatch(postcss, /tailwind/i);

  const globalCss = readFileSync(
    join(projectRoot, "src/app/globals.css"),
    "utf8",
  );
  assert.doesNotMatch(globalCss, /@tailwind|@apply/);
});
