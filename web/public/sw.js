// Service Worker de Telos -- Fase 3 del plan de migración. Esto es lo
// que Streamlit no puede registrar (issue #11665, sin resolver), y el
// motivo real de toda esta migración: sin esto no hay forma de recibir
// una notificación del sistema operativo con la pestaña cerrada.
self.addEventListener("push", (event) => {
  let datos = {};
  try {
    datos = event.data ? event.data.json() : {};
  } catch {
    datos = { titulo: "Telos", cuerpo: event.data ? event.data.text() : "" };
  }

  const titulo = datos.titulo || "Telos";
  event.waitUntil(self.registration.showNotification(titulo, { body: datos.cuerpo || "" }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((lista) => {
      for (const cliente of lista) {
        if ("focus" in cliente) return cliente.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow("/");
      return undefined;
    }),
  );
});
