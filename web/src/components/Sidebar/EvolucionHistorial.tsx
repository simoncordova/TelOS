"use client";

import { useState } from "react";

import { fechaCorta } from "@/lib/fecha";
import type { Textos } from "@/lib/i18n";
import { ICONOS_FASE, NOMBRES_FASE } from "@/lib/i18n";
import type { FichaSnapshot, Idioma } from "@/lib/types";

// Port de "Tu evolución" en ui/app.py: el historial de versiones nunca
// se sobrescribe (spec sección 9, privacidad/versionado) -- esto lo hace
// visible, no solo un dato interno. st.expander -> <details> nativo.
// Línea de tiempo vertical (no solo texto plano) -- pedido explícito
// del dueño del producto probando la app real ("podría ser algo más
// visual").
export function EvolucionHistorial({ idioma, t, ficha }: { idioma: Idioma; t: Textos; ficha: FichaSnapshot }) {
  const [abierto, setAbierto] = useState(false);

  const versiones = [...ficha.historial];
  if (ficha.existe && ficha.actual) versiones.push(ficha.actual);
  versiones.sort((a, b) => (a.fecha < b.fecha ? -1 : a.fecha > b.fecha ? 1 : 0));
  versiones.reverse();

  return (
    <div className="rounded-xl bg-surface">
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
      >
        {t.evolucion_titulo}
        <span className="text-foreground/50">{abierto ? "▲" : "▼"}</span>
      </button>
      {abierto && (
        <div className="px-3 pb-3 text-sm">
          {versiones.length === 0 ? (
            <p className="text-foreground/60">{t.evolucion_vacio}</p>
          ) : (
            <ol className="flex flex-col">
              {versiones.map((version, i) => (
                <li key={i} className="relative flex gap-3 pb-4 last:pb-0">
                  {/* Línea conectora + ícono de la fase, como una posta
                      de tiempo -- oculta en el último elemento (no hay
                      "después" que conectar). */}
                  <div className="flex flex-col items-center">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/20 text-sm">
                      {ICONOS_FASE[version.fase] ?? "•"}
                    </span>
                    {i < versiones.length - 1 && <span className="mt-1 w-px flex-1 bg-primary/30" />}
                  </div>
                  <div className="pt-0.5">
                    <p className="font-medium">{NOMBRES_FASE[idioma][version.fase] ?? version.fase}</p>
                    <p className="text-xs text-foreground/50">{fechaCorta(version.fecha)}</p>
                    <p className="text-foreground/70">{version.motivo_version}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
