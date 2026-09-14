// Espejo de api/esquemas.py -- nombres en camelCase del lado TS, las
// claves que cruzan la red (JSON) siguen siendo las de Python.

export type Idioma = "es" | "en";

export type Mensaje = {
  rol: "user" | "assistant";
  texto: string;
};

export type FichaVersion = {
  fase: number;
  datos: Record<string, unknown>;
  motivo_version: string;
  fecha: string;
};

export type FichaSnapshot = {
  existe: boolean;
  actual: FichaVersion | null;
  historial: FichaVersion[];
  racha: number;
  vista_resumen: string;
  nombre: string | null;
};

// Fase 2 (Sintetizador): un propósito candidato, ya estructurado por el
// backend -- ver agents/_modelo.py::CandidatoProposito. No parsear texto
// libre del lado del frontend, estos tres campos son la fuente de
// verdad para la tarjeta editorial (ver Sintesis/PropositoSelector.tsx).
export type CandidatoProposito = {
  frase: string;
  explicacion: string;
  ejemplo: string;
};

export type EventoTurno =
  | { evento: "mensaje"; datos: { fase: number; texto: string; opciones: string[]; candidatos: CandidatoProposito[] } }
  | { evento: "ficha"; datos: FichaSnapshot }
  | { evento: "error"; datos: { detalle: string } }
  | { evento: "done"; datos: Record<string, never> };

// --- Selector visual Ikigai (Fase 1) -- espejo de
// tools/categorias_ikigai.py y api/esquemas.py::ConfirmarSeleccionRequest/
// SeleccionConfirmadaResponse. "L"/"G"/"V"/"N" son las 4 dimensiones del
// Ikigai (ver ETIQUETAS_DIMENSION); "valores" es un paso aparte, no una
// dimensión más.

export type VerboIkigai = {
  id: string;
  label: string;
  desc: string;
  dims: string; // ej. "LG"
  dominios: string[];
};

export type DominioIkigai = { label: string; desc: string };

export type HojaIkigai = { id: string; label: string; desc: string; dims: string };

export type CategoriasFase1 = {
  dimensiones: string[];
  etiquetasDimension: Record<string, string>;
  verbos: VerboIkigai[];
  dominios: Record<string, DominioIkigai>;
  hojas: Record<string, HojaIkigai[]>;
  valoresDisponibles: string[];
  maxValores: number;
};

// --- Fase 4: 4 árboles independientes (uno por pregunta fija) -- espejo
// de tools/categorias_sistema.py. Nodo con `hijos` opcional (2 niveles).

export type NodoCategoriaSistema = {
  id: string;
  label: string;
  desc?: string;
  hijos?: NodoCategoriaSistema[];
};

export type CategoriasFase4 = {
  preguntas: string[];
  categorias: Record<string, NodoCategoriaSistema[]>;
};

export type SeleccionConfirmada = {
  cobertura: Record<string, number> | null;
  respuestas: Record<string, unknown> | null;
  mostrar_valores: boolean;
  puede_cerrar: boolean;
  cerrado: boolean;
  mensaje_cierre: string | null;
  fase_actual: number;
};

// Chat de apoyo de Fase 1 (ver ArbolSelector.tsx): búsqueda sobre la
// taxonomía fija, nunca crea categorías -- ver
// agents/asistente_categorias.py. Los tres ids solo vienen presentes
// cuando encontrada=true, y ya fueron re-validados por el backend contra
// la taxonomía real.
export type SugerenciaCategoria = {
  encontrada: boolean;
  verbo_id: string | null;
  dominio_id: string | null;
  hoja_id: string | null;
  explicacion: string;
};

// Fase 5 (Vista de resumen): botón "Agregar a mi calendario de Google" --
// espejo de api/esquemas.py::CrearEventoCalendarioResponse. `url_autorizacion`
// viene poblada (y confirmado=false) cuando todavía hace falta que la
// persona autorice el acceso -- se muestra como link real, nunca
// parseado de `mensaje`.
export type EventoCalendarioResultado = {
  confirmado: boolean;
  mensaje: string;
  url_autorizacion: string | null;
};
