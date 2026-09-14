"use client";

import { useState } from "react";

import type { CandidatoProposito, Idioma } from "@/lib/types";
import { AccionesCuenta } from "../AccionesCuenta";

const TEXTOS = {
  es: {
    faseLabel: "Entender · tu propósito",
    cerrarSesion: "Cerrar sesión",
    titulo: "Elige tu propósito",
    cargando: "Armando tus propósitos candidatos…",
    procesando: "Procesando tu respuesta…",
    ejemploLabel: "Ejemplo:",
    escribirTuyo: "Escribir el mío",
    combinarPlaceholder: "Escribí tu propia versión…",
    combinarBoton: "Enviar",
  },
  en: {
    faseLabel: "Understand · your purpose",
    cerrarSesion: "Sign out",
    titulo: "Choose your purpose",
    cargando: "Putting together your candidate purposes…",
    procesando: "Processing your response…",
    ejemploLabel: "Example:",
    escribirTuyo: "Write your own version",
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
  pregunta: string; // kept in props for API compat but no longer rendered
  candidatos: CandidatoProposito[];
  cargando: boolean;
  onElegir: (frase: string) => void;
  onEscribirLibre: (texto: string) => void;
}) {
  const t = TEXTOS[idioma];
  const [libreAbierto, setLibreAbierto] = useState(false);
  const [libre, setLibre] = useState("");

  function toggleLibre() {
    setLibreAbierto((v) => !v);
  }

  function enviarLibre() {
    const texto = libre.trim();
    if (!texto || cargando) return;
    setLibre("");
    setLibreAbierto(false);
    onEscribirLibre(texto);
  }

  // Three distinct states:
  // 1. cargando=true, candidatos=[] → initial fetch or after free-text clears cards
  // 2. cargando=true, candidatos>0 → user just clicked a card (processing the choice)
  // 3. cargando=false → idle, show whatever candidatos we have
  const cargandoInicial = cargando && candidatos.length === 0;
  const procesando = cargando; // covers both cases — buttons disabled, spinner shown

  return (
    <div
      style={{
        height: "100%",
        minHeight: 0,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        background:
          "radial-gradient(70% 45% at 50% 0%, rgba(226,164,74,.13) 0%, rgba(226,164,74,0) 60%), linear-gradient(#fcfaf7 0%, #f5f1ea 55%, #efe8dd 100%)",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
      }}
    >
      {/* ── header ── */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 18,
          padding: "16px clamp(18px,5vw,56px) 8px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/telos-brand.png"
            alt="TelOS"
            style={{
              width: 32,
              height: 32,
              borderRadius: 9,
              objectFit: "cover",
              objectPosition: "50% 34%",
              background: "#1d1b33",
              flexShrink: 0,
            }}
          />
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span
              style={{
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                fontSize: 12.5,
                letterSpacing: ".34em",
                textTransform: "uppercase",
              }}
            >
              Telos
            </span>
            <span
              style={{
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                fontSize: 9.5,
                letterSpacing: ".16em",
                textTransform: "uppercase",
                color: "#6b6459",
              }}
            >
              {t.faseLabel}
            </span>
          </div>
        </div>
        <AccionesCuenta
          idioma={idioma}
          onCambiarIdioma={onCambiarIdioma}
          requiereLogin={requiereLogin}
          logoutLabel={t.cerrarSesion}
        />
      </header>

      {/* ── main ── */}
      <main
        style={{
          flex: 1,
          width: "100%",
          maxWidth: 720,
          margin: "0 auto",
          padding: "clamp(24px,5vh,60px) clamp(18px,5vw,56px) 48px",
          display: "flex",
          flexDirection: "column",
          gap: "clamp(12px,2vh,20px)",
        }}
      >
        {/* ── title ── */}
        <h1
          style={{
            margin: 0,
            fontFamily: "var(--font-instrument-serif), Georgia, serif",
            fontWeight: 400,
            fontSize: "clamp(26px,3.2vw,40px)",
            lineHeight: 1.15,
          }}
        >
          {t.titulo}
        </h1>

        {/* ── initial loading state (no candidates yet) ── */}
        {cargandoInicial && (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              style={{
                display: "inline-block",
                width: 14,
                height: 14,
                borderRadius: "50%",
                border: `2px solid ${ACENTO}`,
                borderTopColor: "transparent",
                animation: "telos-spin .7s linear infinite",
                flexShrink: 0,
              }}
            />
            <p style={{ margin: 0, fontSize: 13, color: "#a8a096" }}>{t.cargando}</p>
          </div>
        )}

        {/* ── processing overlay (user sent text / clicked a card) ── */}
        {procesando && candidatos.length > 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "rgba(252,250,247,.92)",
              border: "1px solid #e2dbd0",
              borderRadius: 12,
              padding: "10px 16px",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: 13,
                height: 13,
                borderRadius: "50%",
                border: `2px solid ${ACENTO}`,
                borderTopColor: "transparent",
                animation: "telos-spin .7s linear infinite",
                flexShrink: 0,
              }}
            />
            <p style={{ margin: 0, fontSize: 13, color: "#6b6459" }}>{t.procesando}</p>
          </div>
        )}

        {/* ── model intro paragraph (shown only with candidates) ── */}
        {!procesando && candidatos.length > 0 && pregunta && (
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "#6b6459", maxWidth: "60ch" }}>
            {pregunta.split("\n")[0].substring(0, 200)}
            {pregunta.length > 200 ? "…" : ""}
          </p>
        )}

        {/* ── candidato buttons ── */}
        {candidatos.map((candidato, i) => (
          <div
            key={i}
            style={{
              animation: "telos-rise .45s ease both",
              animationDelay: `${i * 70}ms`,
            }}
          >
            {/* clickable purpose button */}
            <button
              type="button"
              disabled={procesando}
              onClick={() => onElegir(candidato.frase)}
              style={{
                width: "100%",
                textAlign: "left",
                background: "#fcfaf7",
                border: "1.5px solid #d8d0c4",
                borderRadius: 14,
                padding: "14px 18px",
                cursor: procesando ? "default" : "pointer",
                opacity: procesando ? 0.55 : 1,
                display: "flex",
                flexDirection: "column",
                gap: 4,
                transition: "border-color .15s, box-shadow .15s",
              }}
              onMouseEnter={(e) => {
                if (!procesando) {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "#1b1917";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 2px 10px rgba(27,25,23,.08)";
                }
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "#d8d0c4";
                (e.currentTarget as HTMLButtonElement).style.boxShadow = "none";
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-instrument-serif), Georgia, serif",
                  fontSize: "clamp(15px,1.8vw,20px)",
                  lineHeight: 1.3,
                  color: "#1b1917",
                  fontWeight: 500,
                }}
              >
                {candidato.frase}
              </span>
              {candidato.explicacion && (
                <span style={{ fontSize: 12, lineHeight: 1.4, color: "#6b6459" }}>
                  {candidato.explicacion.substring(0, 100)}
                  {candidato.explicacion.length > 100 ? "…" : ""}
                </span>
              )}
            </button>

            {/* example below the button */}
            {candidato.ejemplo && (
              <div
                style={{
                  display: "flex",
                  gap: 6,
                  alignItems: "flex-start",
                  marginTop: 3,
                  paddingLeft: 12,
                  fontSize: "11px",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-ibm-plex-mono), monospace",
                    fontSize: 8,
                    letterSpacing: ".16em",
                    textTransform: "uppercase",
                    color: ACENTO,
                    paddingTop: 1,
                    flexShrink: 0,
                    whiteSpace: "nowrap",
                  }}
                >
                  {t.ejemploLabel}
                </span>
                <p
                  style={{
                    margin: 0,
                    fontSize: 11,
                    lineHeight: 1.35,
                    color: "#7a726a",
                    fontStyle: "italic",
                  }}
                >
                  {candidato.ejemplo.substring(0, 120)}
                  {candidato.ejemplo.length > 120 ? "…" : ""}
                </p>
              </div>
            )}
          </div>
        ))}

        {/* ── "write your own" option — hidden while processing ── */}
        {!procesando && (
          !libreAbierto ? (
            <button
              type="button"
              onClick={toggleLibre}
              style={{
                width: "100%",
                textAlign: "left",
                background: "transparent",
                border: "1.5px dashed #c8c0b4",
                borderRadius: 16,
                padding: "18px 22px",
                cursor: "pointer",
                fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
                fontSize: "clamp(14px,1.6vw,17px)",
                color: "#6b6459",
                transition: "border-color .15s",
                animation: `telos-rise .45s ease both`,
                animationDelay: `${candidatos.length * 70}ms`,
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "#8c7e6e";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "#c8c0b4";
              }}
            >
              {t.escribirTuyo}…
            </button>
          ) : (
            <div
              style={{
                border: "1.5px solid #1b1917",
                borderRadius: 16,
                background: "#fcfaf7",
                padding: "14px 16px",
                display: "flex",
                gap: 12,
                flexWrap: "wrap",
                alignItems: "center",
                animation: "telos-rise .25s ease both",
              }}
            >
              <input
                autoFocus
                value={libre}
                onChange={(e) => setLibre(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") enviarLibre();
                  if (e.key === "Escape") setLibreAbierto(false);
                }}
                placeholder={t.combinarPlaceholder}
                style={{
                  flex: 1,
                  minWidth: 200,
                  border: "none",
                  background: "transparent",
                  outline: "none",
                  fontSize: 14.5,
                  color: "#1b1917",
                }}
              />
              <button
                onClick={enviarLibre}
                disabled={!libre.trim()}
                style={{
                  border: "1px solid #1b1917",
                  background: "#1b1917",
                  color: "#f7f4ef",
                  borderRadius: 999,
                  padding: "10px 20px",
                  fontSize: 13,
                  cursor: "pointer",
                  opacity: !libre.trim() ? 0.6 : 1,
                }}
              >
                {t.combinarBoton}
              </button>
            </div>
          )
        )}
      </main>
    </div>
  );
}
