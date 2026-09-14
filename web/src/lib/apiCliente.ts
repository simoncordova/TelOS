"use client";

// Fetch desde el navegador (a diferencia de lib/api.ts / lib/auth.ts,
// que corren en el servidor) -- siempre rutas relativas: CloudFront
// enruta /api/* al mismo origen que sirve Next.js (ver infra/stacks/
// telos_stack.py, DistribucionWeb), así que nunca hace falta CORS ni
// conocer una URL absoluta acá. `credentials: "include"` manda la
// cookie de sesión (HttpOnly, api/auth.py) en cada request.
import type { CategoriasFase1, CategoriasFase3, CategoriasFase4, EventoCalendarioResultado, FichaSnapshot, Idioma, SeleccionConfirmada, SugerenciaCategoria } from "./types";

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

// Fases 1/4 pueden cerrar por selección visual, fuera del pipeline de
// texto -- esto arranca al agente de la fase siguiente si es
// conversacional (ver agents/orquestador.py::SesionTelos.
// continuar_tras_seleccion). Llamar SOLO cuando confirmarSeleccion
// devuelva `cerrado: true`.
export function continuarSesion(idioma: Idioma): Promise<Response> {
  return streamPost("/api/sesion/continuar", { idioma });
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

async function jsonFetch<T>(ruta: string, init: RequestInit): Promise<T> {
  const respuesta = await fetch(ruta, { credentials: "include", ...init });
  if (!respuesta.ok) throw new Error(`${ruta} devolvió ${respuesta.status}`);
  return respuesta.status === 204 ? (undefined as T) : respuesta.json();
}

// --- Selector visual (Fases 1/3/4) -- ver api/main.py::obtener_categorias/
// confirmar_seleccion/confirmar_valores. Un solo GET trae el árbol/selector
// completo; la navegación entre niveles es 100% client-side, sin otra
// llamada de red hasta confirmar una hoja real. ---

export function obtenerCategoriasFase1(idioma: Idioma): Promise<CategoriasFase1> {
  return jsonFetch(`/api/categorias/1?idioma=${idioma}`, { method: "GET" });
}

export function obtenerCategoriasFase3(idioma: Idioma): Promise<CategoriasFase3> {
  return jsonFetch(`/api/categorias/3?idioma=${idioma}`, { method: "GET" });
}

export function obtenerCategoriasFase4(idioma: Idioma): Promise<CategoriasFase4> {
  return jsonFetch(`/api/categorias/4?idioma=${idioma}`, { method: "GET" });
}

export function confirmarSeleccion(params: {
  fase: number;
  nodoId: string;
  idioma: Idioma;
  detalleLibre?: string;
  preguntaId?: string;
}): Promise<SeleccionConfirmada> {
  return jsonFetch("/api/seleccion/confirmar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fase: params.fase,
      nodo_id: params.nodoId,
      idioma: params.idioma,
      detalle_libre: params.detalleLibre ?? null,
      pregunta_id: params.preguntaId ?? null,
    }),
  });
}

export function confirmarValores(valores: string[], idioma: Idioma): Promise<{ valores: string[] }> {
  return jsonFetch("/api/seleccion/valores", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ valores, idioma }),
  });
}

// Fase 1: cierre explícito (botón "Ver mi propósito"), nunca automático
// al llegar al mínimo -- ver agents/orquestador.py::SesionTelos.
// cerrar_fase_1_manual. Llamar continuarSesion() justo después para
// arrancar al Sintetizador (Fase 2).
export function cerrarFase1(idioma: Idioma): Promise<SeleccionConfirmada> {
  return jsonFetch("/api/seleccion/cerrar-fase1", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idioma }),
  });
}

// Chat de apoyo de Fase 1 (ver ArbolSelector.tsx): busca, entre las
// categorías fijas que ya existen, la que mejor encaje con lo que la
// persona describió -- ver api/main.py::sugerir_categoria_endpoint /
// agents/asistente_categorias.py. Nunca crea categorías nuevas.
export function sugerirCategoria(descripcion: string, idioma: Idioma): Promise<SugerenciaCategoria> {
  return jsonFetch("/api/categorias/sugerir", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ descripcion, idioma }),
  });
}

// --- Push (Fase 3 del plan de migración) ---

export function obtenerConfigPush(): Promise<{ configurado: boolean; clavePublica: string }> {
  return jsonFetch("/api/push/config", { method: "GET" });
}

export function suscribirPush(suscripcion: PushSubscriptionJSON): Promise<void> {
  return jsonFetch("/api/push/suscripcion", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(suscripcion),
  });
}

export function desuscribirPush(endpoint: string): Promise<void> {
  return jsonFetch("/api/push/suscripcion", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint }),
  });
}

export function enviarPruebaPush(idioma: Idioma): Promise<{ enviados: number; invalidasEliminadas: number }> {
  return jsonFetch("/api/push/enviar-prueba", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idioma }),
  });
}

// Fase 5 (Vista de resumen): agenda el sistema ya definido en el Google
// Calendar real de la persona -- ver api/main.py::
// crear_evento_calendario_endpoint. El backend lee la ficha del lado del
// servidor, así que este POST no manda body.
export function crearEventoCalendario(): Promise<EventoCalendarioResultado> {
  return jsonFetch("/api/calendario/crear-evento", { method: "POST" });
}
