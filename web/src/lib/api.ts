// Base URL de la API (api/main.py) para fetch desde componentes de
// servidor (Server Components, incluida la carga inicial de página) --
// no desde el navegador. fetch() de Node no acepta URLs relativas como
// el del navegador sí, así que acá SIEMPRE hace falta una URL absoluta:
//   - En producción (infra/stacks/telos_stack.py): API_INTERNAL_URL
//     apunta a http://localhost:8000 -- API y Next.js corren en la misma
//     instancia EC2 con --network host, así que esto nunca sale a
//     internet ni pasa por CloudFront.
//   - En desarrollo local: NEXT_PUBLIC_API_URL (ver .env.example).
// Un futuro fetch desde el navegador (Fase 2, ej. el chat interactivo)
// sí puede usar rutas relativas ("/api/...") porque CloudFront enruta
// /api/* al mismo origen (ver plan de migración sección C) -- no
// necesita esta constante.
export const BASE_URL = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "";

export async function obtenerSalud(): Promise<{ estado: string } | null> {
  try {
    const respuesta = await fetch(`${BASE_URL}/api/salud`, { cache: "no-store" });
    if (!respuesta.ok) return null;
    return await respuesta.json();
  } catch {
    return null;
  }
}

export async function obtenerAuthConfig(): Promise<{ requiereLogin: boolean }> {
  try {
    const respuesta = await fetch(`${BASE_URL}/api/auth/config`, { cache: "no-store" });
    if (!respuesta.ok) return { requiereLogin: true };
    return await respuesta.json();
  } catch {
    return { requiereLogin: true };
  }
}
