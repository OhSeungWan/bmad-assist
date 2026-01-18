/**
 * Playwright Configuration for bmad-assist Dashboard E2E Tests
 *
 * Story 16.7 ATDD: Context Menu System
 *
 * Prerequisites:
 * 1. Install Playwright: npm install -D @playwright/test
 * 2. Install browsers: npx playwright install
 * 3. Start dashboard: bmad-assist serve --port 9600
 *
 * Run tests:
 * - All tests: npx playwright test --config tests/e2e/playwright.config.ts
 * - Headed mode: npx playwright test --headed
 * - Debug mode: npx playwright test --debug
 * - Single file: npx playwright test dashboard/context-menu.spec.ts
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './dashboard',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: process.env.DASHBOARD_URL || 'http://localhost:9600',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ],

  /* Run dashboard server before tests */
  webServer: {
    command: 'bmad-assist serve --port 9600',
    port: 9600,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },

  /* Test timeout */
  timeout: 30000,

  /* Expect timeout for assertions */
  expect: {
    timeout: 5000,
  },
});
