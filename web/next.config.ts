import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" -- imagen Docker liviana (solo el server compilado +
  // node_modules podados), en vez de copiar todo node_modules/ al
  // contenedor final. Ver web/Dockerfile.
  output: "standalone",
  // Los e2e (web/playwright.config.ts) pegan a 127.0.0.1 -- sin esto,
  // el dev server de Next.js bloquea los recursos de HMR por origen
  // cruzado (127.0.0.1 vs localhost cuentan como distintos) y el e2e
  // nunca hidrata. Solo afecta al modo dev, no a `next build`/producción.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // En producción, CloudFront enruta /api/* directo a la API -- el
  // contenedor de Next.js nunca ve esas rutas (ver infra/stacks/
  // telos_stack.py, DistribucionWeb). En desarrollo local no hay
  // CloudFront: sin este rewrite, los fetch del navegador a rutas
  // relativas "/api/..." (lib/apiCliente.ts, a propósito same-origin
  // para no necesitar CORS) le pegan al propio Next.js dev server, que
  // no tiene esas rutas -- 404 real, encontrado corriendo los e2e de
  // Playwright contra un navegador de verdad. Reutiliza la misma
  // API_INTERNAL_URL que ya usan los Server Components (lib/api.ts).
  async rewrites() {
    const apiBase = process.env.API_INTERNAL_URL;
    if (!apiBase) return [];
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
};

export default nextConfig;
