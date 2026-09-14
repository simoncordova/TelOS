import type { Idioma } from "./types";

// Vocabulario de "momento del viaje" que ve la persona -- NO el nombre
// interno de cada fase/agente (Explorador, Sintetizador, Estratega de
// Sistemas, Seguimiento; esos siguen existiendo tal cual en
// agents/orquestador.py, solo dejan de mostrarse en la UI). Pedido
// explícito del dueño del producto (14/09/2026): "la experiencia no debe
// sentirse como cuatro fases" -- Fase 2 (Sintetizador, arma el propósito)
// se muestra como el momento "Entender". La entrada `3` se mantiene
// solo para poder seguir mostrando el nombre de una versión vieja en
// "Tu evolución" (de fichas guardadas antes del 14/09/2026, cuando Fase 3
// -- Coach de Validación -- todavía existía y se eliminó del flujo por
// completo) -- una sesión nueva nunca vuelve a producir esa fase.
export const NOMBRES_FASE: Record<Idioma, Record<number, string>> = {
  es: { 0: "Bienvenida", 1: "Descubrir", 2: "Entender", 3: "Entender", 4: "Construir", 5: "Sostener" },
  en: { 0: "Welcome", 1: "Discover", 2: "Understand", 3: "Understand", 4: "Build", 5: "Sustain" },
};

export const ICONOS_FASE: Record<number, string> = {
  1: "🔎",
  2: "🪞",
  3: "🧭",
  4: "🛠️",
  5: "🔁",
};

export type Textos = {
  logout_button: string;
  connected_as: string;
  saludo_nombre: string;
  fase_label: string;
  racha_label: string;
  checkin_toast: string;
  chat_placeholder: string;
  panel_titulo: string;
  panel_proposito: string;
  panel_sistema: string;
  panel_vacio_proposito: string;
  panel_vacio_sistema: string;
  opciones_titulo: string;
  opciones_submit: string;
  resumen_titulo: string;
  camino_peek_vacio: string;
  camino_peek_fase1: string;
  evolucion_titulo: string;
  evolucion_vacio: string;
  exportar_boton: string;
  error_generico: string;
  error_estado_titulo: string;
  error_estado_texto: string;
  error_estado_boton: string;
  tu_proposito_label: string;
  tu_sistema_label: string;
  detalles_boton: string;
  cerrar_boton: string;
  push_titulo: string;
  push_activar: string;
  push_activando: string;
  push_activado: string;
  push_desactivar: string;
  push_probar: string;
  push_error: string;
  push_error_denegado_previo: string;
  push_error_tecnico: string;
  push_prueba_resultado: string;
  calendario_agregar_boton: string;
  calendario_agregando: string;
  calendario_reintentar_boton: string;
  calendario_autorizar_boton: string;
  calendario_pendiente_autorizacion: string;
  calendario_error: string;
  // Sustain view
  sustain_proposito_kicker: string;
  sustain_sistema_kicker: string;
  sustain_ejecutado_boton: string;
  sustain_ejecutado_registrado: string;
  sustain_cumplimiento_kicker: string;
  sustain_cumplimiento_veces: string; // "{n} de {total} veces esta semana"
  sustain_periodo_semana: string;
  sustain_sin_frecuencia: string;
  sustain_descubrir_kicker: string;
  sustain_descubrir_desc: string;
};

export const TEXTOS: Record<Idioma, Textos> = {
  es: {
    logout_button: "Cerrar sesión",
    connected_as: "Conectado como {usuario_id}",
    saludo_nombre: "Hola, {nombre}",
    fase_label: "Tu momento",
    racha_label: "🔥 Racha",
    checkin_toast: "🔥 ¡Racha de {racha}! Seguís sosteniendo tu sistema.",
    chat_placeholder: "Escribe aquí...",
    panel_titulo: "Tus resultados",
    panel_proposito: "Propósito",
    panel_sistema: "Sistema",
    panel_vacio_proposito: "Todavía no lo definiste.",
    panel_vacio_sistema: "Todavía no lo definiste.",
    opciones_titulo: "Elegí una opción, o escribí tu respuesta abajo:",
    opciones_submit: "Elegir",
    resumen_titulo: "Tu resumen",
    camino_peek_vacio: "Todavía no hay nada guardado acá.",
    camino_peek_fase1: 'Acá arrancó todo: valores, momentos de flow, qué harías sin que te paguen, tu legado, qué evitás aunque "deberías".',
    evolucion_titulo: "Tu evolución",
    evolucion_vacio: "Todavía no hay versiones guardadas.",
    exportar_boton: "⬇️ Descargar tu ficha",
    error_generico: "Uy, algo falló de nuestro lado. Probá de nuevo en un momento.",
    error_estado_titulo: "Falló la solución",
    error_estado_texto: "Algo se rompió del lado de la app y no sabemos en qué paso estás. Tu progreso no se perdió -- recargá la página para retomarlo.",
    error_estado_boton: "Recargar",
    tu_proposito_label: "Tu propósito",
    tu_sistema_label: "Tu sistema",
    detalles_boton: "Detalles",
    cerrar_boton: "Cerrar",
    push_titulo: "Notificaciones",
    push_activar: "🔔 Activar notificaciones",
    push_activando: "Activando...",
    push_activado: "🔔 Notificaciones activadas",
    push_desactivar: "Desactivar",
    push_probar: "Enviar una de prueba",
    push_error: "No se pudo activar. Revisá los permisos de notificaciones del navegador.",
    push_error_denegado_previo: "Tu navegador ya tiene las notificaciones bloqueadas para este sitio desde antes -- no alcanza con volver a tocar el botón. Abrí la configuración del sitio en tu navegador (el ícono de candado o \"i\" al lado de la dirección) y habilitá las notificaciones ahí, después probá de nuevo.",
    push_error_tecnico: "No se pudo activar por un error técnico: {detalle}",
    push_prueba_resultado: "Enviadas: {enviados}",
    calendario_agregar_boton: "📅 Agregar a mi calendario de Google",
    calendario_agregando: "Agregando...",
    calendario_reintentar_boton: "Reintentar",
    calendario_autorizar_boton: "Autorizar acceso a Google Calendar",
    calendario_pendiente_autorizacion: "Necesitamos que autorices el acceso a tu Google Calendar primero.",
    calendario_error: "No se pudo agregar a tu calendario. Probá de nuevo en un momento.",
    sustain_proposito_kicker: "Tu propósito",
    sustain_sistema_kicker: "Tu sistema",
    sustain_ejecutado_boton: "✓ Sistema ejecutado",
    sustain_ejecutado_registrado: "¡Registrado!",
    sustain_cumplimiento_kicker: "Cumplimiento esta semana",
    sustain_cumplimiento_veces: "{n} de {total} veces",
    sustain_periodo_semana: "Esta semana",
    sustain_sin_frecuencia: "Sin frecuencia definida",
    sustain_descubrir_kicker: "Tu mapa Ikigai",
    sustain_descubrir_desc: "El cruce de lo que amás, en lo que sos bueno, lo que el mundo necesita y por lo que te pueden pagar — donde nació este propósito.",
  },
  en: {
    logout_button: "Sign out",
    connected_as: "Signed in as {usuario_id}",
    saludo_nombre: "Hi, {nombre}",
    fase_label: "Your stage",
    racha_label: "🔥 Streak",
    checkin_toast: "🔥 {racha}-streak! You're keeping up your system.",
    chat_placeholder: "Type here...",
    panel_titulo: "Your results",
    panel_proposito: "Purpose",
    panel_sistema: "System",
    panel_vacio_proposito: "Not defined yet.",
    panel_vacio_sistema: "Not defined yet.",
    opciones_titulo: "Pick one, or type your own answer below:",
    opciones_submit: "Choose",
    resumen_titulo: "Your summary",
    camino_peek_vacio: "Nothing saved here yet.",
    camino_peek_fase1: 'This is where it all started: values, flow moments, what you\'d do for free, your legacy, what you avoid even though you "should."',
    evolucion_titulo: "Your evolution",
    evolucion_vacio: "No saved versions yet.",
    exportar_boton: "⬇️ Download your ficha",
    error_generico: "Oops, something failed on our end. Try again in a moment.",
    error_estado_titulo: "The setup failed",
    error_estado_texto: "Something broke on the app's side and we can't tell what step you're on. Your progress wasn't lost -- reload the page to pick it back up.",
    error_estado_boton: "Reload",
    tu_proposito_label: "Your purpose",
    tu_sistema_label: "Your system",
    detalles_boton: "Details",
    cerrar_boton: "Close",
    push_titulo: "Notifications",
    push_activar: "🔔 Enable notifications",
    push_activando: "Enabling...",
    push_activado: "🔔 Notifications enabled",
    push_desactivar: "Disable",
    push_probar: "Send a test one",
    push_error: "Couldn't enable it. Check your browser's notification permissions.",
    push_error_denegado_previo: "Your browser already has notifications blocked for this site from before -- clicking the button again won't help. Open this site's settings in your browser (the lock or \"i\" icon next to the address) and enable notifications there, then try again.",
    push_error_tecnico: "Couldn't enable it due to a technical error: {detalle}",
    push_prueba_resultado: "Sent: {enviados}",
    calendario_agregar_boton: "📅 Add to my Google Calendar",
    calendario_agregando: "Adding...",
    calendario_reintentar_boton: "Retry",
    calendario_autorizar_boton: "Authorize Google Calendar access",
    calendario_pendiente_autorizacion: "We need you to authorize access to your Google Calendar first.",
    calendario_error: "Couldn't add it to your calendar. Try again in a moment.",
    sustain_proposito_kicker: "Your purpose",
    sustain_sistema_kicker: "Your system",
    sustain_ejecutado_boton: "✓ System executed",
    sustain_ejecutado_registrado: "Logged!",
    sustain_cumplimiento_kicker: "This week's compliance",
    sustain_cumplimiento_veces: "{n} of {total} times",
    sustain_periodo_semana: "This week",
    sustain_sin_frecuencia: "No frequency defined",
    sustain_descubrir_kicker: "Your Ikigai map",
    sustain_descubrir_desc: "The intersection of what you love, what you're good at, what the world needs, and what you can be paid for — where this purpose was born.",
  },
};
