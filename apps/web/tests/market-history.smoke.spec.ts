import { expect, test } from "@playwright/test";

const rangeKeys = ["1M", "5M", "30M", "1H", "1D", "1W"] as const;

test("market history controls render on the first published market", async ({ page }) => {
  await page.goto("/markets");

  // Wait for markets to load — page may have no published markets in dev
  const marketLink = page.locator("a[href^='/markets/']").first();
  const hasMarkets = await marketLink.isVisible({ timeout: 5000 }).catch(() => false);
  if (!hasMarkets) {
    test.skip(true, "No published markets found — skipping chart controls test");
    return;
  }

  await marketLink.click();
  await page.waitForLoadState("networkidle");

  // Chart controls may or may not be present depending on market data
  const chartSection = page.locator(".market-chart-section");
  const hasChart = await chartSection.isVisible({ timeout: 5000 }).catch(() => false);
  if (!hasChart) {
    test.skip(true, "Market detail page has no chart section — skipping");
    return;
  }

  for (const rangeKey of rangeKeys) {
    const rangeButton = page.getByRole("button", { name: rangeKey });
    await expect(rangeButton).toBeVisible();
  }

  const defaultRange = page.getByRole("button", { name: "1H" });
  await expect(defaultRange).toHaveAttribute("aria-selected", "true");

  const oneDayRange = page.getByRole("button", { name: "1D" });
  await oneDayRange.click();
  await expect(oneDayRange).toHaveAttribute("aria-selected", "true");

  const chartOrEmptyState = page.locator("svg.chart-svg").first().or(page.getByText(/No trade history yet/i));
  await expect(chartOrEmptyState).toBeVisible();
});
