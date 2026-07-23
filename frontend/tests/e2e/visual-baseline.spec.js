import { expect, test } from "@playwright/test";

async function login(page) {
  await page.goto("/login");
  await page.getByLabel("Employee ID").fill("EMP-001");
  await page.getByLabel("Password", { exact: true }).fill("Password123!");
  await page.getByRole("button", { name: "Access portal" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-hidden="true"].animate-spin')).toHaveCount(0, {
    timeout: 30_000,
  });
}

test("login page desktop and mobile visual baseline", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/login");
  await settle(page);
  await expect(page).toHaveScreenshot("login-desktop.png", { fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await settle(page);
  await expect(page).toHaveScreenshot("login-mobile.png", { fullPage: true });
});

test("authenticated application route visual baseline", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);

  const routes = [
    ["/dashboard", "Dashboard", "dashboard.png"],
    ["/submit", "New Submission", "submit.png"],
    ["/search", "Submissions", "search.png"],
    ["/reports", "Reports", "reports.png"],
    ["/sessions", "Parliamentary Sessions", "sessions.png"],
    ["/users", "Users", "users.png"],
  ];

  for (const [route, heading, snapshot] of routes) {
    await page.goto(route);
    await settle(page);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
    await expect(page).toHaveScreenshot(snapshot, { fullPage: true });
  }

  const recordsResponse = await page.request.get("/api/records?limit=1");
  expect(recordsResponse.ok()).toBeTruthy();
  const records = await recordsResponse.json();
  expect(records.length).toBeGreaterThan(0);

  await page.goto(`/results/${records[0].id}`);
  await settle(page);
  await expect(page.getByRole("heading", { name: "Result Record" })).toBeVisible();
  await expect(page).toHaveScreenshot("result-detail.png", { fullPage: true });

  await page.goto("/audit");
  await settle(page);
  await expect(page.getByRole("heading", { name: "Audit Trail" })).toBeVisible();
  await expect(page).toHaveScreenshot("audit.png", {
    fullPage: true,
    mask: [page.locator("table")],
  });
});

test("dashboard mobile visual baseline", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await settle(page);
  await expect(page).toHaveScreenshot("dashboard-mobile.png", { fullPage: true });
});
