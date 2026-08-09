import { defineConfig, devices } from "@playwright/test";

/**
 * E2E config. A plain static server (Python's http.server) serves the project
 * root so the showcase can load the built Carbon bundle and CSS over HTTP with
 * correct MIME types (ES modules are blocked over file://).
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8123",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "python -m http.server 8123",
    url: "http://127.0.0.1:8123",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
