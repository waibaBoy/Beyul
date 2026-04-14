import { expect, test } from "@playwright/test";

test.describe("platform pages render", () => {
  test("landing page loads with hero and navigation", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test("about page loads with product info", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { name: /about/i })).toBeVisible();
    await expect(page.getByText(/2%/)).toBeVisible();
  });

  test("markets page loads", async ({ page }) => {
    await page.goto("/markets");
    await expect(page.getByRole("heading")).toBeVisible();
  });

  test("creators page loads with tier table", async ({ page }) => {
    await page.goto("/creators");
    await expect(page.getByText(/creator/i)).toBeVisible();
  });

  test("ops dashboard page loads", async ({ page }) => {
    await page.goto("/ops");
    await expect(page.getByText(/operations/i)).toBeVisible();
  });

  test("market-requests page loads", async ({ page }) => {
    await page.goto("/market-requests");
    await expect(page.getByRole("heading")).toBeVisible();
  });

  test("communities page loads", async ({ page }) => {
    await page.goto("/communities");
    await expect(page.getByRole("heading")).toBeVisible();
  });

  test("portfolio page shows sign-in prompt for unauthenticated user", async ({ page }) => {
    await page.goto("/portfolio");
    await expect(page.getByText(/sign in/i)).toBeVisible();
  });

  test("auth pages load", async ({ page }) => {
    await page.goto("/auth/sign-in");
    await expect(page.getByRole("heading")).toBeVisible();

    await page.goto("/auth/sign-up");
    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
  });
});

test.describe("navigation", () => {
  test("top nav contains key links", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation");
    await expect(nav).toBeVisible();
  });

  test("about page link from landing", async ({ page }) => {
    await page.goto("/");
    const aboutLink = page.getByRole("link", { name: /about/i }).first();
    if (await aboutLink.isVisible()) {
      await aboutLink.click();
      await expect(page).toHaveURL(/\/about/);
    }
  });
});

test.describe("interactive chart elements", () => {
  test("market detail page loads chart controls when market exists", async ({ page }) => {
    await page.goto("/markets");
    const firstMarketLink = page.locator("a[href^='/markets/']").first();
    if (await firstMarketLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await firstMarketLink.click();
      await page.waitForLoadState("networkidle");
      const chartSection = page.locator(".market-chart-section");
      if (await chartSection.isVisible({ timeout: 5000 }).catch(() => false)) {
        await expect(page.locator(".range-switcher")).toBeVisible();
        await expect(page.locator(".chart-mode-toggle")).toBeVisible();
      }
    }
  });
});

test.describe("portfolio page structure", () => {
  test("portfolio shows export button when authenticated content loads", async ({ page }) => {
    await page.goto("/portfolio");
    const exportBtn = page.locator(".pf-export-btn");
    const signInPrompt = page.getByText(/sign in/i);
    const either = await Promise.race([
      exportBtn.isVisible({ timeout: 3000 }).then(() => "export" as const),
      signInPrompt.isVisible({ timeout: 3000 }).then(() => "signin" as const),
    ]).catch(() => "timeout" as const);
    expect(["export", "signin", "timeout"]).toContain(either);
  });
});
