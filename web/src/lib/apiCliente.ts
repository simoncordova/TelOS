"use client";

// Fetch desde el navegador (a diferencia de lib/api.ts / lib/auth.ts,
// que corren en el servidor) -- siempre rutas relativas: CloudFront
// enruta /api/* al mismo origen que sirve Next.js (ver infra/stacks/
// telos_stack.py, DistribucionWeb), así que nunca hace falta CORS ni
// conocer una URL absoluta acá. `credentials: "include"` manda la
// cookie de sesión (HttpOnly, api/auth.py) en cada request.
import type { FichaSnapshot, Idioma } from "./types";

async function streamPost(ruta: string, cuerpo: unknown): Promise<Response> {
  const respuesta = await fetch(ruta, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
  if (!respuesta.ok) {
    throw new Error(`${ruta} devolvió ${respuesta.status}`);
  }
  return respuesta;
}

export function abrirSesion(idioma: Idioma): Promise<Response> {
  return streamPost("/api/sesion/abrir", { idioma });
}

export function enviarMensaje(texto: string, idioma: Idioma): Promise<Response> {
  return streamPost("/api/sesion/mensaje", { texto, idioma });
}

export async function obtenerFicha(idioma: Idioma): Promise<FichaSnapshot> {
  const respuesta = await fetch(`/api/ficha?idioma=${idioma}`, { credentials: "include" });
  if (!respuesta.ok) throw new Error(`GET /api/ficha devolvió ${respuesta.status}`);
  return respuesta.json();
}

export function urlExportarFicha(idioma: Idioma): string {
  return `/api/ficha/exportar?idioma=${idioma}`;
}

export function urlLogin(idioma: Idioma): string {
  return `/api/auth/login?idioma=${idioma}`;
}

export function urlLogout(): string {
  return "/api/auth/logout";
}
