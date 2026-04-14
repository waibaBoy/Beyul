import { expect, test } from "@playwright/test";

test.describe("signup compliance skeleton", () => {
  test("sign-up page shows RG notice, legal links, and gates submit on checkboxes", async ({ page }) => {
    await page.goto("/auth/sign-up");

    await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Important information \(Australia\)/i })).toBeVisible();
    await expect(page.getByText(/National Gambling Helpline/i)).toBeVisible();

    const submit = page.getByRole("button", { name: "Create account" });
    await expect(submit).toBeDisabled();

    await page.getByLabel("Email").fill("smoke-compliance@example.com");
    await page.getByLabel("Password", { exact: true }).fill("Smoke-test-pass-1");
    await page.getByLabel("Username").fill("smoke_compliance_user");
    await page.getByLabel("Display name").fill("Smoke Compliance");
    await expect(submit).toBeDisabled();

    await page.getByTestId("signup-age-confirm").check();
    await expect(submit).toBeDisabled();

    await page.getByTestId("signup-terms-confirm").check();
    await expect(submit).toBeEnabled();

    const termsLink = page.getByRole("link", { name: "Terms of Service" });
    await expect(termsLink).toHaveAttribute("href", "/legal/terms");
  });

  test("legal draft pages render", async ({ page }) => {
    await page.goto("/legal/terms");
    await expect(page.getByRole("heading", { name: /Terms of Service \(draft\)/i })).toBeVisible();

    await page.goto("/legal/privacy");
    await expect(page.getByRole("heading", { name: /Privacy Policy \(draft\)/i })).toBeVisible();
  });
});
