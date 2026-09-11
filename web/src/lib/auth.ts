// Auth del lado servidor -- solo lo usan Server Components (page.tsx),
// nunca el navegador: la cookie de sesión es HttpOnly a propósito
// (api/auth.py), así que JS de cliente no puede leerla ni falta que
// pueda. Un Server Component sí puede reenviarla en el header Cookie de
// un fetch hecho desde el servidor -- eso es lo único que hace esto.
import "server-only";
import { cookies } from "next/headers";

import { BASE_URL } from "./api";

export type UsuarioActual = { usuarioId: string; nombre: string | null };

export async function obtenerUsuarioActual(): Promise<UsuarioActual | null> {
  const jar = await cookies();
  try {
    const respuesta = await fetch(`${BASE_URL}/api/auth/me`, {
      headers: { cookie: jar.toString() },
      cache: "no-store",
    });
    if (!respuesta.ok) return null;
    const cuerpo = await respuesta.json();
    return { usuarioId: cuerpo.usuarioId, nombre: cuerpo.nombre };
  } catch {
    return null;
  }
}
