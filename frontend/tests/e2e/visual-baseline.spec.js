import { expect, test } from "@playwright/test";

const SNAPSHOT_TIME = new Date("2026-07-23T10:00:00+02:00");

async function login(page) {
  await page.clock.setFixedTime(SNAPSHOT_TIME);
  const response = await page.request.post("/api/auth/login", {
    data: {
      employeeId: "EMP-001",
      password: "Password123!",
    },
  });
  expect(response.ok()).toBeTruthy();
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Account menu for Lilian Mwape" })).toBeVisible();
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
    ["search", "/search", "Submissions Register", "search.png"],
    ["reports", "/reports", "Reports", "reports.png"],
    ["sessions", "/sessions", "Parliamentary Sessions", "sessions.png"],
    ["users", "/users", "Users", "users.png"],
    ["notifications", "/notifications", "Notifications", "notifications.png"],
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

test("keyword search displays matches from full record content", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);
  await page.goto("/search");
  await settle(page);

  const searchResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/search")
      && response.request().method() === "POST",
  );
  await page.getByLabel("Search submissions").fill("qualified");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  expect((await searchResponse).ok()).toBeTruthy();

  await expect(page.getByText("Matched content: qualified")).toBeVisible();
  await expect(
    page.getByText(/increase qualified staffing levels/i),
  ).toBeVisible();
});

test("submission filters stay collapsed until requested and can be reset", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);
  await page.goto("/search");
  await settle(page);

  await expect(page.getByLabel("Session")).toHaveCount(0);
  await page.getByRole("button", { name: "Filters", exact: true }).click();
  await expect(page.getByLabel("Session")).toBeVisible();
  await page.getByLabel("Item Type").selectOption("Question");
  await page.getByRole("button", { name: "Apply filters", exact: true }).click();
  await expect(page.getByLabel("Session")).toHaveCount(0);

  await page.getByRole("button", { name: /Filters/ }).click();
  await expect(page.getByRole("button", { name: "Reset filters", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Reset filters", exact: true }).click();
});

test("top bar opens notifications and account logout", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);

  await page.getByRole("link", { name: "Open notifications" }).click();
  await page.waitForURL(/\/notifications$/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Notifications", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Account menu for Lilian Mwape" }).click();
  await page.getByRole("menuitem", { name: "Log out" }).click();
  await page.waitForURL(/\/login$/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});
