"use client";

import { useState } from "react";

import type { Textos } from "@/lib/i18n";
import { ICONOS_FASE, NOMBRES_FASE } from "@/lib/i18n";
import type { Idioma } from "@/lib/types";

// Port del "mapa del camino" de ui/app.py: las 5 fases como paradas
// (✅/🔵/⚪), cada una un popover clickeable para espiar lo que ya se
// definió ahí sin salir del chat. Ya funciona como indicador de
// progreso por sí solo -- no se le suma una barra de "% completado" al
// lado, mismo criterio que la versión Streamlit.
export function JourneyMap({
  idioma,
  t,
  faseActual,
  proposito,
  sistema,
}: {
  idioma: Idioma;
  t: Textos;
  faseActual: number;
  proposito: string | null | undefined;
  sistema: string | null | undefined;
}) {
  const [abierta, setAbierta] = useState<number | null>(null);

  return (
    <div className="relative flex gap-2 px-4 pt-3">
      {[1, 2, 3, 4, 5].map((numeroFase) => {
        const icono = numeroFase < faseActual ? "✅" : numeroFase === faseActual ? "🔵" : "⚪";
        return (
          <div key={numeroFase} className="relative flex-1">
            <button
              type="button"
              onClick={() => setAbierta((v) => (v === numeroFase ? null : numeroFase))}
              className="w-full rounded-full bg-surface py-1.5 text-center text-sm"
            >
              {icono} {ICONOS_FASE[numeroFase]}
            </button>
            {abierta === numeroFase && (
              <div className="absolute top-full left-0 z-10 mt-1 w-56 rounded-xl border border-surface bg-background p-3 text-sm shadow-lg">
                <p className="mb-1 font-semibold">{NOMBRES_FASE[idioma][numeroFase]}</p>
                {numeroFase === 1 ? (
                  <p className="text-foreground/70">{t.camino_peek_fase1}</p>
                ) : numeroFase === 2 || numeroFase === 3 ? (
                  <p>{proposito || t.camino_peek_vacio}</p>
                ) : (
                  <p>{sistema || t.camino_peek_vacio}</p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
