// Port 1:1 de _TEXTOS / _NOMBRES_FASE / _ICONOS_FASE en ui/app.py -- las
// claves y el copy no cambian, esto es solo el mismo vocabulario en un
// objeto TS en vez de un dict Python. Si el spec cambia el copy, este
// archivo cambia junto con ui/app.py, no por separado.
import type { Idioma } from "./types";

export const NOMBRES_FASE: Record<Idioma, Record<number, string>> = {
  es: { 0: "Bienvenida", 1: "Explorador", 2: "Sintetizador", 3: "Coach de Validación", 4: "Estratega de Sistemas", 5: "Seguimiento" },
  en: { 0: "Welcome", 1: "Explorer", 2: "Synthesizer", 3: "Validation Coach", 4: "Systems Strategist", 5: "Follow-up" },
};

export const ICONOS_FASE: Record<number, string> = {
  1: "🔎",
  2: "🪞",
  3: "🧭",
  4: "🛠️",
  5: "🔁",
};

export type Textos = {
  caption: string;
  login_button: string;
  logout_button: string;
  connected_as: string;
  saludo_nombre: string;
  fase_label: string;
  racha_label: string;
  checkin_toast: string;
  chat_placeholder: string;
  idioma_label: string;
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
  bienvenida_titulo: string;
  bienvenida_texto: string;
  error_generico: string;
  push_titulo: string;
  push_no_soportado: string;
  push_activar: string;
  push_activando: string;
  push_activado: string;
  push_desactivar: string;
  push_probar: string;
  push_error: string;
  push_prueba_resultado: string;
};

export const TEXTOS: Record<Idioma, Textos> = {
  es: {
    caption: "El propósito no es una meta, es un horizonte.",
    login_button: "Iniciar sesión",
    logout_button: "Cerrar sesión",
    connected_as: "Conectado como {usuario_id}",
    saludo_nombre: "Hola, {nombre}",
    fase_label: "Fase actual",
    racha_label: "🔥 Racha",
    checkin_toast: "🔥 ¡Racha de {racha}! Seguís sosteniendo tu sistema.",
    chat_placeholder: "Escribe aquí...",
    idioma_label: "Idioma / Language",
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
    bienvenida_titulo: "👋 Bienvenido a Telos",
    bienvenida_texto:
      "Vamos a explorar tu propósito de vida en una conversación corta, en 5 pasos:\n\n" +
      "1. 🔎 **Explorador** — ponés en palabras lo que te mueve\n" +
      "2. 🪞 **Sintetizador** — te reflejamos 2 o 3 propósitos posibles\n" +
      "3. 🧭 **Coach de Validación** — lo ponemos a prueba con tu propia experiencia\n" +
      "4. 🛠️ **Estratega de Sistemas** — lo convertimos en un hábito concreto\n" +
      "5. 🔁 **Seguimiento** — check-ins breves cada vez que vuelvas\n\n" +
      "No es una meta con fecha límite — es un horizonte. Para arrancar, contame cómo te llamas 👇",
    error_generico: "Uy, algo falló de nuestro lado. Probá de nuevo en un momento.",
    push_titulo: "Notificaciones",
    push_no_soportado: "Tu navegador no soporta notificaciones push.",
    push_activar: "🔔 Activar notificaciones",
    push_activando: "Activando...",
    push_activado: "🔔 Notificaciones activadas",
    push_desactivar: "Desactivar",
    push_probar: "Enviar una de prueba",
    push_error: "No se pudo activar. Revisá los permisos de notificaciones del navegador.",
    push_prueba_resultado: "Enviadas: {enviados}",
  },
  en: {
    caption: "Purpose isn't a goal to reach, it's a horizon.",
    login_button: "Sign in",
    logout_button: "Sign out",
    connected_as: "Signed in as {usuario_id}",
    saludo_nombre: "Hi, {nombre}",
    fase_label: "Current phase",
    racha_label: "🔥 Streak",
    checkin_toast: "🔥 {racha}-streak! You're keeping up your system.",
    chat_placeholder: "Type here...",
    idioma_label: "Idioma / Language",
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
    bienvenida_titulo: "👋 Welcome to Telos",
    bienvenida_texto:
      "We're going to explore your life purpose in a short conversation, in 5 steps:\n\n" +
      "1. 🔎 **Explorer** — put into words what moves you\n" +
      "2. 🪞 **Synthesizer** — we reflect back 2 or 3 possible purposes\n" +
      "3. 🧭 **Validation Coach** — we stress-test it against your own experience\n" +
      "4. 🛠️ **Systems Strategist** — we turn it into a concrete habit\n" +
      "5. 🔁 **Follow-up** — brief check-ins every time you come back\n\n" +
      "It's not a goal with a deadline — it's a horizon. To get started, tell me your name 👇",
    error_generico: "Oops, something failed on our end. Try again in a moment.",
    push_titulo: "Notifications",
    push_no_soportado: "Your browser doesn't support push notifications.",
    push_activar: "🔔 Enable notifications",
    push_activando: "Enabling...",
    push_activado: "🔔 Notifications enabled",
    push_desactivar: "Disable",
    push_probar: "Send a test one",
    push_error: "Couldn't enable it. Check your browser's notification permissions.",
    push_prueba_resultado: "Sent: {enviados}",
  },
};
