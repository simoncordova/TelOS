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

export type EventoTurno =
  | { evento: "mensaje"; datos: { fase: number; texto: string; opciones: string[] } }
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
  hijos?: NodoCategoriaSistema[];
};

export type CategoriasFase4 = {
  preguntas: string[];
  categorias: Record<string, NodoCategoriaSistema[]>;
};

// --- Fase 3: selector plano de áreas de vida -- espejo de
// tools/categorias_validacion.py.

export type AreaVida = { id: string; label: string };

export type CategoriasFase3 = { areas: AreaVida[] };

export type SeleccionConfirmada = {
  cobertura: Record<string, number> | null;
  respuestas: Record<string, unknown> | null;
  etapa: string | null;
  mensaje_apertura_refinado: string | null;
  mostrar_valores: boolean;
  puede_cerrar: boolean;
  cerrado: boolean;
  mensaje_cierre: string | null;
  fase_actual: number;
};
