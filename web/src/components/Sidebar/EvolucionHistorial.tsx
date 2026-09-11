"use client";

import { useState } from "react";

import { fechaCorta } from "@/lib/fecha";
import type { Textos } from "@/lib/i18n";
import { NOMBRES_FASE } from "@/lib/i18n";
import type { FichaSnapshot, Idioma } from "@/lib/types";

// Port de "Tu evolución" en ui/app.py: el historial de versiones nunca
// se sobrescribe (spec sección 9, privacidad/versionado) -- esto lo hace
// visible, no solo un dato interno. st.expander -> <details> nativo.
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
        <div className="flex flex-col gap-2 px-3 pb-3 text-sm">
          {versiones.length === 0 ? (
            <p className="text-foreground/60">{t.evolucion_vacio}</p>
          ) : (
            versiones.map((version, i) => (
              <div key={i}>
                <p className="font-medium">
                  {fechaCorta(version.fecha)} — {NOMBRES_FASE[idioma][version.fase] ?? version.fase}
                </p>
                <p className="text-foreground/70">{version.motivo_version}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
