"use client";

// Helpers del lado navegador para Web Push -- ver public/sw.js (el
// Service Worker que recibe el push) y api/push.py (el envío del lado
// servidor). Nada acá se llama solo: siempre a partir de un opt-in
// explícito de la persona (ver Notifications/PushOptIn.tsx) -- nunca un
// prompt de permisos automático al cargar la página.

function base64UrlAUint8Array(base64Url: string): Uint8Array {
  const relleno = "=".repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + relleno).replace(/-/g, "+").replace(/_/g, "/");
  const crudo = atob(base64);
  const bytes = new Uint8Array(crudo.length);
  for (let i = 0; i < crudo.length; i++) bytes[i] = crudo.charCodeAt(i);
  return bytes;
}

export function pushSoportado(): boolean {
  return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window;
}

async function registrarServiceWorker(): Promise<ServiceWorkerRegistration> {
  return navigator.serviceWorker.register("/sw.js");
}

export async function obtenerSuscripcionActual(): Promise<PushSubscription | null> {
  if (!pushSoportado()) return null;
  const registro = await navigator.serviceWorker.getRegistration();
  if (!registro) return null;
  return registro.pushManager.getSubscription();
}

// Lanza si el permiso se deniega -- quien llama (PushOptIn) le muestra
// el error a la persona en vez de fallar en silencio.
export async function suscribirseAPush(clavePublicaVapid: string): Promise<PushSubscriptionJSON> {
  const registro = await registrarServiceWorker();
  const permiso = await Notification.requestPermission();
  if (permiso !== "granted") {
    throw new Error("Permiso de notificaciones denegado");
  }
  const existente = await registro.pushManager.getSubscription();
  const suscripcion =
    existente ??
    (await registro.pushManager.subscribe({
      userVisibleOnly: true,
      // Cast necesario: TS tipa Uint8Array como genérico sobre
      // ArrayBufferLike, pero PushSubscriptionOptionsInit pide
      // específicamente un ArrayBufferView<ArrayBuffer> -- el valor en
      // runtime es válido igual, esto es solo un desajuste de tipos del
      // lib.dom.d.ts con TS 5.7+.
      applicationServerKey: base64UrlAUint8Array(clavePublicaVapid) as BufferSource,
    }));
  return suscripcion.toJSON();
}

// Devuelve el endpoint que quedó desuscripto (para que el backend borre
// esa suscripción puntual), o null si no había ninguna.
export async function desuscribirseDePush(): Promise<string | null> {
  const suscripcion = await obtenerSuscripcionActual();
  if (!suscripcion) return null;
  const endpoint = suscripcion.endpoint;
  await suscripcion.unsubscribe();
  return endpoint;
}
