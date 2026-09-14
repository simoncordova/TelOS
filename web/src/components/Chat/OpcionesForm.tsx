"use client";

import { useState } from "react";

// Port de la sección "opciones_pendientes" de ui/app.py: cuando el
// agente de la fase actual ofreció opciones cerradas (ver
// agents/_modelo.py::crear_tool_presentar_opciones), se muestran como
// botones pill en vez de obligar a escribir la elección -- el chat de
// abajo sigue disponible para quien prefiera escribir su propia respuesta.
// Estilo consistente con el sistema visual warm de la maqueta.
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
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
        borderTop: "1px solid #e6ddd0",
        background: "rgba(240,236,228,.55)",
        padding: "12px 20px",
      }}
    >
      <p
        style={{
          margin: 0,
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 9.5,
          letterSpacing: ".16em",
          textTransform: "uppercase",
          color: "#6b6459",
        }}
      >
        {titulo}
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {opciones.map((opcion) => {
          const on = elegida === opcion;
          return (
            <button
              key={opcion}
              type="button"
              onClick={() => setElegida(opcion)}
              style={{
                border: `1px solid ${on ? "#a4552f" : "#e2dbd0"}`,
                background: on ? "rgba(164,85,47,.08)" : "transparent",
                color: on ? "#1b1917" : "#5d564d",
                borderRadius: 999,
                padding: "9px 16px",
                fontSize: 13.5,
                cursor: "pointer",
                transition: "all .25s ease",
                fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
              }}
            >
              {opcion}
            </button>
          );
        })}
      </div>
      <button
        type="submit"
        disabled={deshabilitado}
        style={{
          alignSelf: "flex-start",
          border: "1px solid #1b1917",
          background: "#1b1917",
          color: "#f7f4ef",
          borderRadius: 999,
          padding: "10px 22px",
          fontSize: 13,
          cursor: "pointer",
          opacity: deshabilitado ? 0.5 : 1,
          fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        }}
      >
        {submitLabel}
      </button>
    </form>
  );
}
