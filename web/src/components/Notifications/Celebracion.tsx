"use client";

import { useEffect } from "react";

// Port de _procesar_turno en ui/app.py: st.balloons() al completar el
// sistema (Fase 4 -> 5, un hito real) y st.toast() al cerrar un
// check-in cumplido -- una vez por hito real, no un gancho de hábito
// repetido en cada mensaje. Streamlit no tiene equivalente nativo en
// JS/CSS puro, así que esto sí es código nuevo (ver
// web/src/app/globals.css para la animación).
export type Festejo = { tipo: "globos" } | { tipo: "toast"; mensaje: string };

const _GLOBOS = ["🎈", "🎉", "🎈", "✨", "🎈"];

export function Celebracion({ festejo, onFin }: { festejo: Festejo | null; onFin: () => void }) {
  useEffect(() => {
    if (!festejo) return;
    const ms = festejo.tipo === "globos" ? 3300 : 3000;
    const id = setTimeout(onFin, ms);
    return () => clearTimeout(id);
  }, [festejo, onFin]);

  if (!festejo) return null;

  if (festejo.tipo === "globos") {
    return (
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-around">
        {_GLOBOS.map((globo, i) => (
          <span
            key={i}
            className="animar-globo text-3xl"
            style={{ animationDelay: `${i * 0.15}s` }}
          >
            {globo}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-full bg-primary px-4 py-2 text-sm text-primary-foreground shadow-lg">
      {festejo.mensaje}
    </div>
  );
}
