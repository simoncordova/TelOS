"use client";

import type { CandidatoProposito } from "@/lib/types";
import type { Idioma } from "@/lib/types";

// Fase 2 (Sintetizador, momento "Entender") -- reemplaza los botones
// genéricos de OpcionesForm para este momento puntual: los 2-3
// candidatos de propósito que arma agents/sintetizador.py ahora llegan
// como datos estructurados (ver tipo CandidatoProposito), así que se
// muestran como tarjetas editoriales -- mismo lenguaje visual que
// ArbolSelector/ValidacionSelector/SistemaSelector (serif grande para el
// contenido central, mono uppercase para los rótulos) en vez del "diseño
// de sintetizador antiguo" (texto plano en una burbuja de chat) que
// motivó este cambio (pedido explícito del dueño del producto,
// 14/09/2026).
//
// El chat de abajo (ChatInput) sigue disponible para quien prefiera
// escribir su propia combinación en vez de elegir una tarjeta tal
// cual -- estas tarjetas son un atajo, no reemplazan al chat.
const TEXTOS = {
  es: {
    titulo: "Elegí un propósito, o combiná partes de varios escribiendo abajo",
    ejemploLabel: "Así se vería",
    elegir: "Elegir este propósito",
  },
  en: {
    titulo: "Pick a purpose, or blend parts of a few by typing below",
    ejemploLabel: "What this looks like",
    elegir: "Choose this purpose",
  },
};

const ACENTO = "#a4552f";

export function CandidatosProposito({
  idioma,
  candidatos,
  deshabilitado,
  onElegir,
}: {
  idioma: Idioma;
  candidatos: CandidatoProposito[];
  deshabilitado: boolean;
  onElegir: (frase: string) => void;
}) {
  const t = TEXTOS[idioma];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        borderTop: "1px solid #e6ddd0",
        background: "rgba(240,236,228,.55)",
        padding: "16px 20px",
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
        {t.titulo}
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 12 }}>
        {candidatos.map((candidato, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 10,
              border: "1px solid #e2dbd0",
              background: "#fcfaf7",
              borderRadius: 16,
              padding: "18px 20px",
            }}
          >
            <p
              style={{
                margin: 0,
                fontFamily: "var(--font-instrument-serif), Georgia, serif",
                fontSize: "clamp(19px,2.3vw,25px)",
                lineHeight: 1.2,
                color: "#1b1917",
              }}
            >
              {candidato.frase}
            </p>

            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: "#5d564d" }}>{candidato.explicacion}</p>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 3,
                borderLeft: `2px solid ${ACENTO}`,
                paddingLeft: 12,
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  fontSize: 9,
                  letterSpacing: ".18em",
                  textTransform: "uppercase",
                  color: ACENTO,
                }}
              >
                {t.ejemploLabel}
              </span>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "#6b6459", fontStyle: "italic" }}>
                {candidato.ejemplo}
              </p>
            </div>

            <button
              type="button"
              disabled={deshabilitado}
              onClick={() => onElegir(candidato.frase)}
              style={{
                alignSelf: "flex-start",
                marginTop: 4,
                border: "1px solid #1b1917",
                background: "#1b1917",
                color: "#f7f4ef",
                borderRadius: 999,
                padding: "9px 18px",
                fontSize: 12.5,
                cursor: deshabilitado ? "default" : "pointer",
                opacity: deshabilitado ? 0.5 : 1,
                fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
                transition: "opacity .2s ease",
              }}
            >
              {t.elegir}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
