import { expect, test } from "@playwright/test";

async function login(page) {
  const response = await page.request.post("/api/auth/login", {
    data: {
      employeeId: "EMP-001",
      password: "Password123!",
    },
  });
  expect(response.ok()).toBeTruthy();
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Lilian Mwape", { exact: true })).toBeVisible();
}

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await expect(page.locator('[aria-hidden="true"].ui-spinner')).toHaveCount(0, {
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

test.describe("authenticated application route visual baseline", () => {
  const routes = [
    ["dashboard", "/dashboard", "Dashboard", "dashboard.png"],
    ["submit", "/submit", "New Submission", "submit.png"],
    ["search", "/search", "Submissions", "search.png"],
    ["reports", "/reports", "Reports", "reports.png"],
    ["sessions", "/sessions", "Parliamentary Sessions", "sessions.png"],
    ["users", "/users", "Users", "users.png"],
  ];

  for (const [name, route, heading, snapshot] of routes) {
    test(`${name} desktop`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await login(page);
      await page.goto(route);
      await settle(page);
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
      await expect(page).toHaveScreenshot(snapshot, { fullPage: true });
    });
  }

  test("result detail desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    const recordsResponse = await page.request.get("/api/records?limit=1");
    expect(recordsResponse.ok()).toBeTruthy();
    const records = await recordsResponse.json();
    expect(records.length).toBeGreaterThan(0);

    await page.goto(`/results/${records[0].id}`);
    await settle(page);
    await expect(page.getByRole("heading", { name: "Result Record" })).toBeVisible();
    await expect(page).toHaveScreenshot("result-detail.png", { fullPage: true });
  });

  test("audit desktop", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await login(page);
    await page.goto("/audit");
    await settle(page);
    await expect(page.getByRole("heading", { name: "Audit Trail" })).toBeVisible();
    await expect(page).toHaveScreenshot("audit.png", {
      fullPage: false,
      mask: [page.locator("table")],
    });
  });
});

test("dashboard mobile visual baseline", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await settle(page);
  await expect(page).toHaveScreenshot("dashboard-mobile.png", { fullPage: true });
});
