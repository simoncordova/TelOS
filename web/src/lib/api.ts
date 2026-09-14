// Base URL de la API (api/main.py) para fetch desde componentes de
// servidor (Server Components, incluida la carga inicial de página) --
// no desde el navegador. fetch() de Node no acepta URLs relativas como
// el del navegador sí, así que acá SIEMPRE hace falta una URL absoluta:
//   - En producción (infra/stacks/telos_stack.py): API_INTERNAL_URL
//     apunta a http://localhost:8000 -- API y Next.js corren en la misma
//     instancia EC2 con --network host, así que esto nunca sale a
//     internet ni pasa por CloudFront.
//   - En desarrollo local: NEXT_PUBLIC_API_URL (ver .env.example).
// El chat/selectores interactivos (todo lo que corre en el navegador, no
// en un Server Component) usan lib/apiCliente.ts en cambio, con rutas
// relativas ("/api/...") -- CloudFront enruta /api/* al mismo origen, así
// que esa parte nunca necesita esta constante.
export const BASE_URL = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "";

export async function obtenerAuthConfig(): Promise<{ requiereLogin: boolean }> {
  try {
    const respuesta = await fetch(`${BASE_URL}/api/auth/config`, { cache: "no-store" });
    if (!respuesta.ok) return { requiereLogin: true };
    return await respuesta.json();
  } catch {
    return { requiereLogin: true };
  }
}
