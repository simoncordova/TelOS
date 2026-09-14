"use client";

import { useState } from "react";

import { crearEventoCalendario } from "@/lib/apiCliente";
import type { Textos } from "@/lib/i18n";
import { parsearSistema } from "@/lib/parseSistema";

const ACENTO = "#a4552f";

// Fase 5 (momento "Sostener"), pedido explícito del dueño del producto
// (14/09/2026): el botón "Continue" que cierra Fase 4 no mostraba nada
// más -- esta tarjeta es la página de resumen real, con el propósito y
// el sistema siempre visibles (mismo estilo que CabeceraFase, no un
// bloque de texto plano) y el botón para agendar el sistema en Google
// Calendar de verdad, con el propósito en el cuerpo del evento (ver
// api/main.py::crear_evento_calendario_endpoint).
export function ResumenCard({
  t,
  proposito,
  sistema,
}: {
  t: Textos;
  proposito: string | null | undefined;
  sistema: string | null | undefined;
}) {
  const [estado, setEstado] = useState<"inactivo" | "cargando" | "ok" | "error">("inactivo");
  const [resultado, setResultado] = useState<{ mensaje: string; url_autorizacion: string | null } | null>(null);
  const filasSistema = sistema ? parsearSistema(sistema) : [];

  async function agregarAlCalendario() {
    setEstado("cargando");
    try {
      const r = await crearEventoCalendario();
      setResultado(r);
      setEstado(r.confirmado || r.url_autorizacion ? "ok" : "error");
    } catch (e) {
      console.error("No se pudo agendar el evento de calendario:", e);
      setResultado(null);
      setEstado("error");
    }
  }

  return (
    <div
      style={{
        margin: "12px 16px 0",
        display: "flex",
        flexDirection: "column",
        gap: 16,
        border: "1px solid #e2dbd0",
        background: "#fcfaf7",
        borderRadius: 20,
        padding: "20px 22px",
      }}
    >
      <h2
        style={{
          margin: 0,
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 9.5,
          letterSpacing: ".16em",
          textTransform: "uppercase",
          color: "#6b6459",
        }}
      >
        {t.resumen_titulo}
      </h2>

      {proposito && (
        <div>
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>
            {t.tu_proposito_label}
          </div>
          <p style={{ margin: "4px 0 0", fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(20px,2.6vw,28px)", lineHeight: 1.25, color: "#1b1917" }}>
            {proposito}
          </p>
        </div>
      )}

      {filasSistema.length > 0 && (
        <div>
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>
            {t.tu_sistema_label}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
            {filasSistema.map(([etiqueta, valor], i) => (
              <span
                key={i}
                style={{
                  border: "1px solid #e2dbd0",
                  background: "#f5f1ea",
                  borderRadius: 999,
                  padding: "5px 12px",
                  fontSize: 12.5,
                  color: "#3b3630",
                }}
              >
                {etiqueta ? <strong style={{ fontWeight: 600 }}>{etiqueta}: </strong> : null}
                {valor}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid #e6ddd0", paddingTop: 14 }}>
        <button
          type="button"
          onClick={agregarAlCalendario}
          disabled={estado === "cargando"}
          style={{
            alignSelf: "flex-start",
            border: "1px solid #1b1917",
            background: "#1b1917",
            color: "#f7f4ef",
            borderRadius: 999,
            padding: "9px 18px",
            fontSize: 12.5,
            cursor: estado === "cargando" ? "default" : "pointer",
            opacity: estado === "cargando" ? 0.6 : 1,
            fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
          }}
        >
          {estado === "cargando" ? t.calendario_agregando : t.calendario_agregar_boton}
        </button>

        {estado === "ok" && resultado && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "#5d564d" }}>{resultado.mensaje}</p>
            {resultado.url_autorizacion && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <p style={{ margin: 0, fontSize: 12.5, color: "#6b6459" }}>{t.calendario_pendiente_autorizacion}</p>
                <a
                  href={resultado.url_autorizacion}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 12.5, color: ACENTO, fontWeight: 600, alignSelf: "flex-start" }}
                >
                  {t.calendario_autorizar_boton}
                </a>
              </div>
            )}
          </div>
        )}

        {estado === "error" && (
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <p style={{ margin: 0, fontSize: 13, color: "#a4552f" }}>{t.calendario_error}</p>
            <button
              type="button"
              onClick={agregarAlCalendario}
              style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "4px 12px", fontSize: 12, cursor: "pointer" }}
            >
              {t.calendario_reintentar_boton}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
