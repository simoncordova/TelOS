"use client";

import { useState } from "react";

import type { Textos } from "@/lib/i18n";
import { NOMBRES_FASE } from "@/lib/i18n";
import type { Idioma } from "@/lib/types";

// Port del "mapa del camino" de ui/app.py -- son los 4 MOMENTOS del
// viaje que ve la persona (Descubrir/Entender/Construir/Sostener, ver
// NOMBRES_FASE en web/src/lib/i18n.ts), no las fases internas. La fase
// interna (1, 2, 4, 5 -- Fase 3, Coach de Validación, se eliminó del
// flujo el 14/09/2026, ver agents/orquestador.py) sigue siendo la
// fuente de verdad en `faseActual`; este componente solo agrupa cómo se
// muestra, nunca cambia qué fase es.
type Momento = { id: string; fases: number[] };
const MOMENTOS: Momento[] = [
  { id: "descubrir", fases: [1] },
  { id: "entender", fases: [2] },
  { id: "construir", fases: [4] },
  { id: "sostener", fases: [5] },
];

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
  const [abierto, setAbierto] = useState<string | null>(null);

  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        gap: 6,
        padding: "10px 20px 4px",
        alignItems: "center",
      }}
    >
      {MOMENTOS.map((momento, idx) => {
        const primeraFase = momento.fases[0];
        const ultimaFase = momento.fases[momento.fases.length - 1];
        const completado = faseActual > ultimaFase;
        const activo = faseActual >= primeraFase && faseActual <= ultimaFase;
        return (
          <div key={momento.id} style={{ position: "relative", flex: 1 }}>
            {/* Línea conectora */}
            {idx > 0 && (
              <div
                style={{
                  position: "absolute",
                  left: "-4px",
                  top: "50%",
                  width: 4,
                  height: 1,
                  background: completado ? "#a4552f" : "#e2dbd0",
                  transform: "translateY(-50%)",
                }}
              />
            )}
            <button
              type="button"
              onClick={() => setAbierto((v) => (v === momento.id ? null : momento.id))}
              style={{
                width: "100%",
                border: `1px solid ${activo ? "#a4552f" : completado ? "#c9bfb0" : "#e2dbd0"}`,
                background: activo ? "rgba(164,85,47,.08)" : completado ? "#f5f1ea" : "transparent",
                borderRadius: 999,
                padding: "6px 8px",
                fontSize: 11,
                color: activo ? "#a4552f" : completado ? "#5d564d" : "#a8a096",
                cursor: "pointer",
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                letterSpacing: ".1em",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                transition: "all .25s ease",
              }}
            >
              {completado ? "✓ " : activo ? "· " : ""}{NOMBRES_FASE[idioma][primeraFase]}
            </button>
            {abierto === momento.id && (
              <div
                style={{
                  position: "absolute",
                  top: "calc(100% + 6px)",
                  left: 0,
                  zIndex: 10,
                  width: 220,
                  background: "#fcfaf7",
                  border: "1px solid #e2dbd0",
                  borderRadius: 14,
                  padding: "12px 14px",
                  fontSize: 13,
                  boxShadow: "0 14px 34px -22px rgba(27,25,23,.5)",
                  fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
                  color: "#1b1917",
                }}
              >
                <p
                  style={{
                    margin: "0 0 6px",
                    fontFamily: "var(--font-ibm-plex-mono), monospace",
                    fontSize: 9,
                    letterSpacing: ".2em",
                    textTransform: "uppercase",
                    color: "#a4552f",
                  }}
                >
                  {NOMBRES_FASE[idioma][primeraFase]}
                </p>
                <p style={{ margin: 0, lineHeight: 1.5, color: "#5d564d" }}>
                  {momento.id === "descubrir"
                    ? t.camino_peek_fase1
                    : momento.id === "entender"
                      ? proposito || t.camino_peek_vacio
                      : sistema || t.camino_peek_vacio}
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
