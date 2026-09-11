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
