import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

// e2e real contra un backend real corriendo en local -- a diferencia de
// tests/api/ (Python, mockea SesionTelos), esto prueba la app de verdad
// de punta a punta: Next.js real, API real, solo Bedrock/AgentCore
// quedan fuera de alcance (sin credenciales de AWS en la mayoría de los
// entornos de desarrollo). Por eso los specs de e2e/ solo cubren lo que
// no necesita Bedrock -- ver el comentario en e2e/chat.spec.ts.
const RAIZ_REPO = path.resolve(__dirname, "..");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: "html",
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      // API en modo dev: TELOS_REQUIRE_LOGIN=0 salta Cognito (mismo
      // mecanismo que ui/app.py), TELOS_FICHA_BACKEND=local no necesita
      // AWS -- global-setup.ts limpia estos archivos antes de correr,
      // así cada corrida arranca de una cuenta nueva.
      command: '".venv/Scripts/python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port 8100',
      cwd: RAIZ_REPO,
      env: { TELOS_REQUIRE_LOGIN: "0", TELOS_FICHA_BACKEND: "local" },
      url: "http://127.0.0.1:8100/api/salud",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- -p 3100",
      cwd: __dirname,
      env: { API_INTERNAL_URL: "http://127.0.0.1:8100" },
      url: "http://127.0.0.1:3100",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
