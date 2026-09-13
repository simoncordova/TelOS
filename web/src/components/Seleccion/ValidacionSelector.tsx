"use client";

import { useEffect, useState } from "react";

import { confirmarSeleccion, obtenerCategoriasFase3 } from "@/lib/apiCliente";
import type { AreaVida, Idioma } from "@/lib/types";

// Fase 3 -- Coach de Validación. Selector funcional simple (mismo
// criterio que SistemaSelector.tsx: prioriza que el flujo funcione de
// punta a punta, no la estética -- se puede re-vestir después). A
// diferencia de Fase 1/4, acá SOLO se resuelven por selección las dos
// primeras etapas (evidencia pasada, fricción futura) -- ver
// agents/orquestador.py::SesionTelos.confirmar_seleccion_validacion.
// Una vez que el backend confirma la 2da elección, devuelve
// `mensaje_apertura_refinado`: la primera propuesta real del coach. A
// partir de ahí la fase es una conversación de texto genuina
// (agents/coach_validacion.py) -- este componente avisa a quien lo usa
// (`onEntrarRefinado`) para que la vista principal pase a ser el chat
// normal de la app (ChatWindow/ChatInput ya existentes, sin duplicar
// esa UI acá).

const TEXTOS = {
  es: {
    tituloPasada: "¿En qué área ya viviste este propósito, aunque en pequeño?",
    tituloFutura: "¿En qué área sería tentador abandonarlo, o chocaría con otra prioridad?",
    detallePlaceholder: "Contá el momento específico (opcional)",
    confirmar: "Confirmar",
    cargando: "Guardando…",
  },
  en: {
    tituloPasada: "In what area have you already lived this purpose, even in a small way?",
    tituloFutura: "In what area would it be tempting to abandon it, or clash with another priority?",
    detallePlaceholder: "Tell the specific moment (optional)",
    confirmar: "Confirm",
    cargando: "Saving…",
  },
} as const;

export function ValidacionSelector({
  idioma,
  onEntrarRefinado,
}: {
  idioma: Idioma;
  onEntrarRefinado: (primerMensaje: string) => void;
}) {
  const t = TEXTOS[idioma];
  const [areas, setAreas] = useState<AreaVida[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [etapa, setEtapa] = useState<"evidencia_pasada" | "friccion_futura">("evidencia_pasada");
  const [areaElegida, setAreaElegida] = useState<string | null>(null);
  const [detalle, setDetalle] = useState("");
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let cancelado = false;
    obtenerCategoriasFase3(idioma)
      .then((d) => {
        if (!cancelado) setAreas(d.areas);
      })
      .catch(() => {
        if (!cancelado) setError(idioma === "es" ? "No se pudo cargar. Recargá la página." : "Couldn't load. Reload the page.");
      });
    return () => {
      cancelado = true;
    };
  }, [idioma]);

  if (error && !areas) return <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-foreground/70">{error}</div>;
  if (!areas) return <div className="flex flex-1 items-center justify-center p-8 text-sm text-foreground/50">…</div>;

  async function confirmar() {
    if (!areaElegida) return;
    setGuardando(true);
    setError(null);
    try {
      const detalleTexto = detalle.trim();
      const resultado = await confirmarSeleccion({
        fase: 3,
        nodoId: areaElegida,
        idioma,
        detalleLibre: detalleTexto || undefined,
      });
      setAreaElegida(null);
      setDetalle("");
      if (resultado.mensaje_apertura_refinado) {
        onEntrarRefinado(resultado.mensaje_apertura_refinado);
      } else {
        setEtapa("friccion_futura");
      }
    } catch {
      setError(idioma === "es" ? "No se pudo guardar. Probá de nuevo." : "Couldn't save. Try again.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
      <h2 className="text-lg font-medium">{etapa === "evidencia_pasada" ? t.tituloPasada : t.tituloFutura}</h2>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {areas.map((a) => (
          <button
            key={a.id}
            disabled={guardando}
            onClick={() => setAreaElegida(a.id)}
            className={`rounded-xl border px-4 py-3 text-left text-sm disabled:opacity-50 ${
              areaElegida === a.id ? "border-primary bg-primary/10" : "border-surface bg-surface/40 hover:border-primary"
            }`}
          >
            {a.label}
          </button>
        ))}
      </div>

      {areaElegida && (
        <div className="flex flex-col gap-3 rounded-xl border border-surface bg-surface/40 p-4">
          <input
            value={detalle}
            onChange={(e) => setDetalle(e.target.value)}
            placeholder={t.detallePlaceholder}
            className="rounded-lg border border-surface bg-transparent px-3 py-2 text-sm outline-none"
          />
          <button
            onClick={confirmar}
            disabled={guardando}
            className="self-start rounded-full bg-primary px-4 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
          >
            {guardando ? t.cargando : t.confirmar}
          </button>
        </div>
      )}
    </div>
  );
}
