import { defineConfig, devices } from "@playwright/test";

const nextCommand = process.platform === "win32"
  ? ".\\node_modules\\.bin\\next.cmd dev"
  : "./node_modules/.bin/next dev";

const webServer = process.env.PLAYWRIGHT_SKIP_WEB_SERVER
  ? undefined
  : {
      command: nextCommand,
      env: {
        API_PROXY_TARGET: "http://127.0.0.1:5000",
      },
      port: 3000,
      reuseExistingServer: !process.env.CI,
    };

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  webServer,
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
