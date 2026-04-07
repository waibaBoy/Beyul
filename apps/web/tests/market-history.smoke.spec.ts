import { expect, test } from "@playwright/test";

const rangeKeys = ["1M", "5M", "30M", "1H", "1D", "1W"] as const;

test("market history controls render on the first published market", async ({ page }) => {
  await page.goto("/markets");

  await expect(page.getByRole("heading", { name: "Published markets" })).toBeVisible();

  const marketLink = page.getByRole("link", { name: "Open market" }).first();
  await expect(marketLink).toBeVisible();
  await marketLink.click();

  await expect(page.getByRole("heading", { name: "Market chart" })).toBeVisible();
  await expect(page.getByText("Market shell")).toBeVisible();

  for (const rangeKey of rangeKeys) {
    const rangeButton = page.getByRole("button", { name: rangeKey });
    await expect(rangeButton).toBeVisible();
  }

  const defaultRange = page.getByRole("button", { name: "1H" });
  await expect(defaultRange).toHaveAttribute("aria-selected", "true");

  const oneDayRange = page.getByRole("button", { name: "1D" });
  await oneDayRange.click();
  await expect(oneDayRange).toHaveAttribute("aria-selected", "true");

  await expect(page.getByText("Candle buckets")).toBeVisible();
  await expect(page.getByText("Probability history")).toBeVisible();
  await expect(page.getByText("Volume bars")).toBeVisible();
  await expect(page.getByText("Window volume")).toBeVisible();

  const chartOrEmptyState = page.locator("svg.chart-svg").first().or(page.getByText(/No trade history yet/i));
  await expect(chartOrEmptyState).toBeVisible();
});
