import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  retries: 0,
  timeout: 30_000,
  use: {
    baseURL,
    headless: true,
    trace: "retain-on-failure"
  },
  reporter: [["list"]],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: "npx next dev --turbopack -p 3000",
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120_000
      }
});
