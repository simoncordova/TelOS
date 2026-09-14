"use client";

import { useState } from "react";

import type { Textos } from "@/lib/i18n";
import { NOMBRES_FASE } from "@/lib/i18n";
import type { Idioma } from "@/lib/types";

// Port del "mapa del camino" de ui/app.py: las 5 fases como paradas,
// cada una clickeable para ver lo que ya se definió ahí.
// Estilo actualizado al sistema visual warm de la maqueta.
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

  const FASE_LABELS: Record<number, string> = {
    1: "Explorar",
    2: "Síntesis",
    3: "Validar",
    4: "Sistema",
    5: "Check-in",
  };

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
      {[1, 2, 3, 4, 5].map((numeroFase, idx) => {
        const completada = numeroFase < faseActual;
        const activa = numeroFase === faseActual;
        return (
          <div key={numeroFase} style={{ position: "relative", flex: 1 }}>
            {/* Línea conectora */}
            {idx > 0 && (
              <div
                style={{
                  position: "absolute",
                  left: "-4px",
                  top: "50%",
                  width: 4,
                  height: 1,
                  background: completada ? "#a4552f" : "#e2dbd0",
                  transform: "translateY(-50%)",
                }}
              />
            )}
            <button
              type="button"
              onClick={() => setAbierta((v) => (v === numeroFase ? null : numeroFase))}
              style={{
                width: "100%",
                border: `1px solid ${activa ? "#a4552f" : completada ? "#c9bfb0" : "#e2dbd0"}`,
                background: activa ? "rgba(164,85,47,.08)" : completada ? "#f5f1ea" : "transparent",
                borderRadius: 999,
                padding: "6px 8px",
                fontSize: 11,
                color: activa ? "#a4552f" : completada ? "#5d564d" : "#a8a096",
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
              {completada ? "✓ " : activa ? "· " : ""}{FASE_LABELS[numeroFase]}
            </button>
            {abierta === numeroFase && (
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
                  {NOMBRES_FASE[idioma][numeroFase]}
                </p>
                <p style={{ margin: 0, lineHeight: 1.5, color: "#5d564d" }}>
                  {numeroFase === 1
                    ? t.camino_peek_fase1
                    : numeroFase === 2 || numeroFase === 3
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
