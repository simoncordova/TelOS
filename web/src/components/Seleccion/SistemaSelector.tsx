"use client";

import { useEffect, useState } from "react";

import { confirmarSeleccion, continuarSesion, obtenerCategoriasFase4 } from "@/lib/apiCliente";
import type { CategoriasFase4, Idioma, NodoCategoriaSistema } from "@/lib/types";

// Fase 4 -- Estratega de Sistemas. Selector funcional simple (Tailwind,
// mismo lenguaje visual que OpcionesForm.tsx) -- a diferencia de Fase 1
// (ArbolSelector), todavía no tiene un diseño propio de Claude Design;
// esto prioriza que el flujo completo (Fases 1-5) funcione de punta a
// punta ya mismo, no la estética. Se puede re-vestir después sin tocar
// la lógica de abajo, que ya calca exacto la mecánica real del backend
// (agents/orquestador.py::SesionTelos.confirmar_seleccion_sistema): 4
// preguntas fijas, en orden fijo, cada una con su propio árbol de 1-2
// niveles + detalle libre opcional. El backend cierra la fase solo al
// responder la 4ta -- este componente no decide nada, solo refleja lo
// que el backend ya guardó.

const ETIQUETAS_PREGUNTA: Record<Idioma, Record<string, string>> = {
  es: {
    accion: "¿Qué acción concreta y pequeña vas a repetir?",
    cuando_donde: "¿Cuándo y dónde exactamente la vas a hacer?",
    metrica: "¿Cómo vas a saber, sin ambigüedad, que la cumpliste?",
    obstaculo: "¿Cuál es el obstáculo más probable, y qué harás cuando aparezca?",
  },
  en: {
    accion: "What small, concrete action will you repeat?",
    cuando_donde: "When and where exactly will you do it?",
    metrica: "How will you know, unambiguously, that you kept it?",
    obstaculo: "What's the likeliest obstacle, and what will you do about it?",
  },
};

const TEXTOS = {
  es: {
    paso: (n: number, total: number) => `Paso ${n} de ${total}`,
    detallePlaceholder: "¿algo más específico? (opcional)",
    confirmar: "Confirmar",
    volver: "← Volver",
    cargando: "Guardando…",
    resumenTitulo: "Tu sistema",
  },
  en: {
    paso: (n: number, total: number) => `Step ${n} of ${total}`,
    detallePlaceholder: "anything more specific? (optional)",
    confirmar: "Confirm",
    volver: "← Back",
    cargando: "Saving…",
    resumenTitulo: "Your system",
  },
} as const;

export function SistemaSelector({ idioma, onCerrado }: { idioma: Idioma; onCerrado: (mensajeCierre?: string) => void }) {
  const t = TEXTOS[idioma];
  const [datos, setDatos] = useState<CategoriasFase4 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preguntaIdx, setPreguntaIdx] = useState(0);
  const [path, setPath] = useState<string[]>([]);
  const [detalle, setDetalle] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let cancelado = false;
    obtenerCategoriasFase4(idioma)
      .then((d) => {
        if (!cancelado) setDatos(d);
      })
      .catch(() => {
        if (!cancelado) setError(idioma === "es" ? "No se pudo cargar. Recargá la página." : "Couldn't load. Reload the page.");
      });
    return () => {
      cancelado = true;
    };
  }, [idioma]);

  if (error && !datos) return <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-foreground/70">{error}</div>;
  if (!datos) return <div className="flex flex-1 items-center justify-center p-8 text-sm text-foreground/50">…</div>;

  const preguntaId = datos.preguntas[preguntaIdx];
  const arbol = datos.categorias[preguntaId] ?? [];

  function nivelActual(): NodoCategoriaSistema[] {
    let nivel = arbol;
    for (const id of path) {
      nivel = nivel.find((n) => n.id === id)?.hijos ?? [];
    }
    return nivel;
  }

  const opciones = nivelActual();
  const enHoja = path.length > 0 && opciones.length === 0;

  async function confirmarHoja() {
    const hojaId = path[path.length - 1];
    setGuardando(true);
    setError(null);
    try {
      const detalleTexto = detalle.trim();
      const resultado = await confirmarSeleccion({
        fase: 4,
        preguntaId,
        nodoId: hojaId,
        idioma,
        detalleLibre: detalleTexto || undefined,
      });
      setPath([]);
      setDetalle("");
      if (resultado.cerrado) {
        await continuarSesion(idioma).catch(() => {});
        onCerrado(resultado.mensaje_cierre ?? undefined);
      } else {
        setPreguntaIdx((i) => i + 1);
      }
    } catch {
      setError(idioma === "es" ? "No se pudo guardar. Probá de nuevo." : "Couldn't save. Try again.");
    } finally {
      setGuardando(false);
    }
  }

  function volver() {
    setPath((p) => p.slice(0, -1));
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
      <div className="text-xs uppercase tracking-wide text-foreground/50">{t.paso(preguntaIdx + 1, datos.preguntas.length)}</div>
      <h2 className="text-lg font-medium">{ETIQUETAS_PREGUNTA[idioma][preguntaId] ?? preguntaId}</h2>

      {error && <p className="text-xs text-red-600">{error}</p>}

      {!enHoja && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {opciones.map((n) => (
            <button
              key={n.id}
              disabled={guardando}
              onClick={() => setPath((p) => [...p, n.id])}
              className="rounded-xl border border-surface bg-surface/40 px-4 py-3 text-left text-sm hover:border-primary disabled:opacity-50"
            >
              {n.label}
            </button>
          ))}
        </div>
      )}

      {enHoja && (
        <div className="flex flex-col gap-3 rounded-xl border border-surface bg-surface/40 p-4">
          <input
            value={detalle}
            onChange={(e) => setDetalle(e.target.value)}
            placeholder={t.detallePlaceholder}
            className="rounded-lg border border-surface bg-transparent px-3 py-2 text-sm outline-none"
          />
          <button
            onClick={confirmarHoja}
            disabled={guardando}
            className="self-start rounded-full bg-primary px-4 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            {guardando ? t.cargando : t.confirmar}
          </button>
        </div>
      )}

      {path.length > 0 && (
        <button onClick={volver} disabled={guardando} className="self-start text-xs text-foreground/60 underline disabled:opacity-50">
          {t.volver}
        </button>
      )}
    </div>
  );
}
