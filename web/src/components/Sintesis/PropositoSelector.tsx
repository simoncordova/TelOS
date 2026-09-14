"use client";

import { useState } from "react";

import type { CandidatoProposito, Idioma } from "@/lib/types";
import { AccionesCuenta } from "../AccionesCuenta";

// Selector visual de Fase 2 (Sintetizador, momento "Entender") -- mismo
// criterio que ArbolSelector.tsx/SistemaSelector.tsx (Fases 1/4): página
// propia de selección visual, NO un chat. Corrección explícita del
// dueño del producto (14/09/2026) sobre el primer intento de este
// cambio: mostrar los candidatos como tarjetas DENTRO del chat (bajo un
// mensaje de texto en ChatWindow) todavía se sentía como chat -- acá los
// 2-3 candidatos que arma agents/sintetizador.py y el marco breve que
// los presenta (`pregunta`, viaja en el evento SSE "mensaje" para Fase
// 2, ver TelosApp.tsx) son el contenido central de toda la pantalla, sin
// ningún historial de mensajes visible.
//
// "Combinar partes de varios" sigue siendo texto libre real -- no se
// puede reducir a un botón porque es una redacción nueva, no una de las
// ya ofrecidas -- pero vive como un campo en esta misma página
// (`onEscribirLibre`, en la práctica el mismo `procesarTurno` que usa el
// chat real de otras fases), nunca como una burbuja de conversación.
const TEXTOS = {
  es: {
    faseLabel: "Entender · tu propósito",
    cerrarSesion: "Cerrar sesión",
    cargando: "Armando tus propósitos candidatos…",
    ejemploLabel: "Así se vería",
    elegir: "Elegir este propósito",
    combinarTitulo: "¿Preferís combinar partes de varios, o escribir el tuyo?",
    combinarPlaceholder: "Escribí tu propia versión…",
    combinarBoton: "Enviar",
  },
  en: {
    faseLabel: "Understand · your purpose",
    cerrarSesion: "Sign out",
    cargando: "Putting together your candidate purposes…",
    ejemploLabel: "What this looks like",
    elegir: "Choose this purpose",
    combinarTitulo: "Prefer to blend parts of a few, or write your own?",
    combinarPlaceholder: "Write your own version…",
    combinarBoton: "Send",
  },
};

const ACENTO = "#a4552f";

export function PropositoSelector({
  idioma,
  onCambiarIdioma,
  requiereLogin,
  pregunta,
  candidatos,
  cargando,
  onElegir,
  onEscribirLibre,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  requiereLogin: boolean;
  pregunta: string;
  candidatos: CandidatoProposito[];
  cargando: boolean;
  onElegir: (frase: string) => void;
  onEscribirLibre: (texto: string) => void;
}) {
  const t = TEXTOS[idioma];
  const [libre, setLibre] = useState("");

  function enviarLibre() {
    const texto = libre.trim();
    if (!texto || cargando) return;
    setLibre("");
    onEscribirLibre(texto);
  }

  return (
    <div
      style={{
        height: "100%",
        minHeight: 0,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        background: "radial-gradient(70% 45% at 50% 0%, rgba(226,164,74,.13) 0%, rgba(226,164,74,0) 60%), linear-gradient(#fcfaf7 0%, #f5f1ea 55%, #efe8dd 100%)",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
      }}
    >
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 18, padding: "16px clamp(18px,5vw,56px) 8px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/telos-brand.png" alt="TelOS" style={{ width: 32, height: 32, borderRadius: 9, objectFit: "cover", objectPosition: "50% 34%", background: "#1d1b33", flexShrink: 0 }} />
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 12.5, letterSpacing: ".34em", textTransform: "uppercase" }}>Telos</span>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: "#6b6459" }}>{t.faseLabel}</span>
          </div>
        </div>
        <AccionesCuenta idioma={idioma} onCambiarIdioma={onCambiarIdioma} requiereLogin={requiereLogin} logoutLabel={t.cerrarSesion} />
      </header>

      <main style={{ flex: 1, width: "100%", maxWidth: 1080, margin: "0 auto", padding: "clamp(20px,5vh,56px) clamp(18px,5vw,56px) 40px", display: "flex", flexDirection: "column", gap: "clamp(18px,3vh,30px)" }}>
        {!pregunta && candidatos.length === 0 ? (
          <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", fontSize: 13, color: "#a8a096" }}>{t.cargando}</div>
        ) : (
          <>
            {pregunta && (
              <h1 style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontWeight: 400, fontSize: "clamp(22px,2.8vw,34px)", lineHeight: 1.2, maxWidth: "44ch" }}>
                {pregunta}
              </h1>
            )}

            {candidatos.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 280px), 1fr))", gap: "clamp(10px,1.4vw,16px)" }}>
                {candidatos.map((candidato, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 12,
                      border: "1px solid #e2dbd0",
                      background: "#fcfaf7",
                      borderRadius: 18,
                      padding: "20px 22px",
                      animation: "telos-rise .5s ease both",
                      animationDelay: `${i * 60}ms`,
                    }}
                  >
                    <p style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(19px,2.3vw,25px)", lineHeight: 1.22, color: "#1b1917" }}>
                      {candidato.frase}
                    </p>

                    <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: "#5d564d" }}>{candidato.explicacion}</p>

                    <div style={{ display: "flex", flexDirection: "column", gap: 3, borderLeft: `2px solid ${ACENTO}`, paddingLeft: 12 }}>
                      <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9, letterSpacing: ".18em", textTransform: "uppercase", color: ACENTO }}>
                        {t.ejemploLabel}
                      </span>
                      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "#6b6459", fontStyle: "italic" }}>{candidato.ejemplo}</p>
                    </div>

                    <button
                      type="button"
                      disabled={cargando}
                      onClick={() => onElegir(candidato.frase)}
                      style={{
                        alignSelf: "flex-start",
                        marginTop: 4,
                        border: "1px solid #1b1917",
                        background: "#1b1917",
                        color: "#f7f4ef",
                        borderRadius: 999,
                        padding: "10px 20px",
                        fontSize: 13,
                        cursor: cargando ? "default" : "pointer",
                        opacity: cargando ? 0.5 : 1,
                      }}
                    >
                      {t.elegir}
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 680, borderTop: "1px solid #e2dbd0", paddingTop: "clamp(14px,2.4vh,22px)" }}>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: "#6b6459" }}>
                {t.combinarTitulo}
              </span>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", border: "1px solid #e2dbd0", background: "#fcfaf7", borderRadius: 16, padding: "14px 16px" }}>
                <input
                  value={libre}
                  onChange={(e) => setLibre(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") enviarLibre();
                  }}
                  disabled={cargando}
                  placeholder={t.combinarPlaceholder}
                  style={{ flex: 1, minWidth: 220, border: "none", background: "transparent", outline: "none", fontSize: 14.5, color: "#1b1917" }}
                />
                <button
                  onClick={enviarLibre}
                  disabled={cargando || !libre.trim()}
                  style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "11px 22px", fontSize: 13, cursor: "pointer", opacity: cargando || !libre.trim() ? 0.6 : 1 }}
                >
                  {t.combinarBoton}
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
