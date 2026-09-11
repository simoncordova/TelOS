"use client";

import { useState } from "react";

// Port de la sección "opciones_pendientes" de ui/app.py: cuando el
// agente de la fase actual ofreció opciones cerradas (ver
// agents/_modelo.py::crear_tool_presentar_opciones), se muestran como
// radio en vez de obligar a escribir la elección -- el chat de abajo
// sigue disponible para quien prefiera escribir su propia respuesta.
export function OpcionesForm({
  titulo,
  submitLabel,
  opciones,
  deshabilitado,
  onElegir,
}: {
  titulo: string;
  submitLabel: string;
  opciones: string[];
  deshabilitado: boolean;
  onElegir: (opcion: string) => void;
}) {
  const [elegida, setElegida] = useState(opciones[0] ?? "");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (elegida) onElegir(elegida);
      }}
      className="flex flex-col gap-2 border-t border-surface bg-surface/60 p-3"
    >
      <p className="text-xs text-foreground/70">{titulo}</p>
      <div className="flex flex-col gap-1">
        {opciones.map((opcion) => (
          <label key={opcion} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="opcion"
              value={opcion}
              checked={elegida === opcion}
              onChange={() => setElegida(opcion)}
            />
            {opcion}
          </label>
        ))}
      </div>
      <button
        type="submit"
        disabled={deshabilitado}
        className="self-start rounded-full bg-primary px-4 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
      >
        {submitLabel}
      </button>
    </form>
  );
}
