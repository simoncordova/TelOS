import { expect, test } from "@playwright/test";

// Backend real (API + AgentCore local), sin Bedrock: este entorno no
// tiene credenciales de AWS, así que estos specs cubren deliberadamente
// solo lo que NO necesita una invocación real al modelo --
// - "Paso 0" (pedir el nombre) es código puro, sin LLM (ver
//   agents/orquestador.py::SesionTelos._pidiendo_nombre).
// - enviar el nombre SÍ dispara una llamada real (_extraer_nombre) --
//   sin credenciales, falla (boto3 puede tardar bastante en agotar su
//   cadena de proveedores de credenciales antes de rendirse, de ahí el
//   timeout largo de ese test), y lo que se prueba acá es que ese fallo
//   se propaga como un error prolijo en el chat (api/sse.py -> evento
//   "error" -> TelosApp.tsx), no que la conversación siga.
// Con credenciales de Bedrock reales, agregar specs que sí completen una
// fase entera es el siguiente paso natural de esta suite.
//
// Serial a propósito: todos los tests de este archivo comparten el
// mismo usuario de desarrollo ("prueba-local", ver api/auth.py --
// TELOS_REQUIRE_LOGIN=0 no permite elegir otro) y por lo tanto la MISMA
// sesión del lado del servidor -- correrlos en paralelo hace que compitan
// por el mismo lock (api/main.py::_obtener_lock) y por el estado
// conversacional del mismo usuario. El orden importa: el primer test
// depende del estado recién limpiado por global-setup.ts.
test.describe.configure({ mode: "serial" });

test.describe("Telos (bypass de login, backend local, sin Bedrock)", () => {
  test("carga en inglés por defecto y pide el nombre sin tocar Bedrock", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Telos" })).toBeVisible();
    await expect(page.getByText(/what's your first name/i)).toBeVisible({ timeout: 15_000 });
  });

  test("un fallo real de Bedrock (sin credenciales) se muestra como error, no como cuelgue", async ({ page }) => {
    test.setTimeout(60_000); // boto3 puede tardar en agotar su cadena de credenciales antes de fallar
    await page.goto("/");
    const input = page.getByPlaceholder(/type here/i);
    await expect(input).toBeEnabled({ timeout: 15_000 });
    await input.fill("Ada");
    await input.press("Enter");
    // "Ada" (usuario) tiene que aparecer optimista de inmediato...
    await expect(page.getByText("Ada", { exact: true })).toBeVisible();
    // ...y el error del backend (Bedrock sin credenciales) tiene que
    // llegar como mensaje, no dejar el chat esperando para siempre.
    await expect(page.getByText(/something failed on our end/i)).toBeVisible({ timeout: 45_000 });
  });

  test("cambiar el idioma a español actualiza el copy de la barra lateral", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Español" }).click();
    await expect(page.getByText("Fase actual")).toBeVisible();
  });

  test("sin VAPID configurado, la sección de notificaciones no se muestra", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Notifications")).toHaveCount(0);
  });

  test("el manifest PWA está enlazado y responde", async ({ page, request }) => {
    await page.goto("/");
    const href = await page.locator('link[rel="manifest"]').getAttribute("href");
    expect(href).toBe("/manifest.json");
    const respuesta = await request.get(href!);
    expect(respuesta.ok()).toBeTruthy();
    const manifest = await respuesta.json();
    expect(manifest.name).toBe("Telos");
  });
});
