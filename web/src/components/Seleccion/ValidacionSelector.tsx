"use client";

import { useEffect, useState } from "react";

import { confirmarSeleccion, obtenerCategoriasFase3 } from "@/lib/apiCliente";
import type { AreaVida, Idioma } from "@/lib/types";

// Fase 3 -- Coach de Validación. Selector de dos etapas (evidencia
// pasada → fricción futura). Una vez que el backend confirma la 2da
// elección devuelve `mensaje_apertura_refinado`: primera propuesta real
// del coach. A partir de ahí la fase es conversación de texto genuina
// (agents/coach_validacion.py) -- este componente avisa vía
// `onEntrarRefinado` para que la vista principal pase al chat normal.
// Sistema de diseño idéntico a ArbolSelector y SistemaSelector:
// inline styles, IBM Plex Mono / Instrument Sans / Instrument Serif,
// paleta #fcfaf7 → #efe8dd, acento #a4552f, animaciones telos-*.

const ACENTO = "#a4552f";

const TEXTOS = {
  es: {
    faseLabel: "Fase 3 · Coach de validación",
    kicker: "Propósito en construcción",
    tituloEvidencia: "¿En qué área ya viviste este propósito, aunque en pequeño?",
    tituloFriccion: "¿En qué área sería tentador abandonarlo, o chocaría con otra prioridad?",
    subEvidencia: "No hace falta que haya sido perfecto. Basta con una señal real.",
    subFriccion: "No es pesimismo: es tener la respuesta lista de antemano.",
    detallePlaceholder: "Contá el momento específico (opcional)",
    confirmar: "Confirmar",
    cargando: "Guardando…",
    etapa1Label: "01 · Evidencia pasada",
    etapa2Label: "02 · Fricción futura",
    ayudaChat: "¿Necesitas aclarar algo?",
    cerrarApoyo: "Cerrar apoyo",
    apoyoTitulo: "Apoyo",
    apoyoSub: "Pregunta lo que necesites aclarar",
    chatPlaceholder: "Escribe tu duda…",
    sugerencias: ["¿Qué significa evidencia?", "¿Por qué la fricción?", "¿Qué pasa si no sé?"],
    mensajeInicialChat:
      "Esta fase sirve para que tu propósito se apoye en algo real que ya viviste, y anticipe dónde puede chocar. Elige el área que más se acerque; después podés dar más detalle.",
    errorCarga: "No se pudo cargar. Recargá la página.",
    error: "No se pudo guardar. Probá de nuevo.",
  },
  en: {
    faseLabel: "Phase 3 · Validation coach",
    kicker: "Purpose in progress",
    tituloEvidencia: "In what area have you already lived this purpose, even in a small way?",
    tituloFriccion: "In what area would it be tempting to abandon it, or clash with another priority?",
    subEvidencia: "It doesn't have to have been perfect. A real signal is enough.",
    subFriccion: "This isn't pessimism: it's having the answer ready ahead of time.",
    detallePlaceholder: "Tell the specific moment (optional)",
    confirmar: "Confirm",
    cargando: "Saving…",
    etapa1Label: "01 · Past evidence",
    etapa2Label: "02 · Future friction",
    ayudaChat: "Need something clarified?",
    cerrarApoyo: "Close support",
    apoyoTitulo: "Support",
    apoyoSub: "Ask whatever you need clarified",
    chatPlaceholder: "Type your question…",
    sugerencias: ["What does evidence mean?", "Why friction?", "What if I don't know?"],
    mensajeInicialChat:
      "This phase grounds your purpose in something real you've already lived, and anticipates where it might clash. Choose the area that fits best; you can add more detail after.",
    errorCarga: "Couldn't load. Reload the page.",
    error: "Couldn't save. Try again.",
  },
} as const;

function respuestaMecanica(bajo: string, idioma: Idioma): string | null {
  if (idioma === "es") {
    if (bajo.includes("evidencia")) return "Evidencia es cualquier momento donde actuaste desde ese propósito, aunque haya sido pequeño o imperfecto. No necesita haber salido bien.";
    if (bajo.includes("fricci")) return "La fricción muestra dónde el propósito va a encontrar resistencia real. Saberlo de antemano es lo que lo hace sostenible.";
    if (bajo.includes("no s") || bajo.includes("segur")) return "Elige el área que más se acerque. Siempre podés dar contexto en el campo de texto para aclarar matices.";
    return "Elige el área que más resuene, aunque no sea perfecta. El detalle opcional ayuda a afinar.";
  }
  if (bajo.includes("evidence")) return "Evidence is any moment where you acted from that purpose, even if small or imperfect. It doesn't need to have gone well.";
  if (bajo.includes("friction")) return "Friction shows where the purpose will meet real resistance. Knowing it ahead of time is what makes it sustainable.";
  if (bajo.includes("don't know") || bajo.includes("not sure")) return "Pick the area that feels closest. You can always add context in the text field to clarify nuances.";
  return "Choose the area that resonates most, even if it's not perfect. The optional detail helps refine it.";
}

export function ValidacionSelector({
  idioma,
  onEntrarRefinado,
}: {
  idioma: Idioma;
  onEntrarRefinado: (primerMensaje: string) => void;
}) {
  const t = TEXTOS[idioma];
  const [areas, setAreas] = useState<AreaVida[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [etapa, setEtapa] = useState<"evidencia_pasada" | "friccion_futura">("evidencia_pasada");
  const [areaElegida, setAreaElegida] = useState<string | null>(null);
  const [detalle, setDetalle] = useState("");
  const [guardando, setGuardando] = useState(false);

  const [chatOpen, setChatOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<{ who: "me" | "bot"; text: string }[]>([
    { who: "bot", text: t.mensajeInicialChat },
  ]);

  useEffect(() => {
    let cancelado = false;
    obtenerCategoriasFase3(idioma)
      .then((d) => {
        if (!cancelado) setAreas(d.areas);
      })
      .catch(() => {
        if (!cancelado) setError(t.errorCarga);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idioma]);

  if (error && !areas)
    return (
      <div
        style={{
          display: "flex",
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          padding: 32,
          textAlign: "center",
          fontSize: 13.5,
          color: "#6b6459",
        }}
      >
        {error}
      </div>
    );

  if (!areas)
    return (
      <div
        style={{
          display: "flex",
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          fontSize: 13,
          color: "#a8a096",
        }}
      >
        …
      </div>
    );

  async function confirmar() {
    if (!areaElegida) return;
    setGuardando(true);
    setError(null);
    try {
      const detalleTexto = detalle.trim();
      const resultado = await confirmarSeleccion({
        fase: 3,
        nodoId: areaElegida,
        idioma,
        detalleLibre: detalleTexto || undefined,
      });
      setAreaElegida(null);
      setDetalle("");
      if (resultado.mensaje_apertura_refinado) {
        onEntrarRefinado(resultado.mensaje_apertura_refinado);
      } else {
        setEtapa("friccion_futura");
      }
    } catch {
      setError(t.error);
    } finally {
      setGuardando(false);
    }
  }

  function enviarChat(texto: string) {
    const limpio = texto.trim();
    if (!limpio) return;
    const respuesta = respuestaMecanica(limpio.toLowerCase(), idioma);
    setMessages((prev) => [
      ...prev,
      { who: "me", text: limpio },
      { who: "bot", text: respuesta ?? t.mensajeInicialChat },
    ]);
    setDraft("");
  }

  const esEvidencia = etapa === "evidencia_pasada";
  const titulo = esEvidencia ? t.tituloEvidencia : t.tituloFriccion;
  const sub = esEvidencia ? t.subEvidencia : t.subFriccion;
  const etapaLabel = esEvidencia ? t.etapa1Label : t.etapa2Label;

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
        position: "relative",
      }}
    >
      <style>{`
        @keyframes telos-rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
        @keyframes telos-fade { from { opacity:0; } to { opacity:1; } }
        @keyframes telos-breathe { 0%,100% { opacity:.55; transform:scale(1); } 50% { opacity:.85; transform:scale(1.035); } }
      `}</style>

      {/* ── Header ── */}
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
          <img src="/telos-brand.png" alt="TelOS" style={{ width: 32, height: 32, borderRadius: 9, objectFit: "cover", objectPosition: "50% 34%", background: "#1d1b33", flexShrink: 0 }} />
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
        <button
          onClick={() => setChatOpen((v) => !v)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 9,
            border: "1px solid #ded7cc",
            background: "rgba(252,250,247,.8)",
            color: "#5d564d",
            borderRadius: 999,
            padding: "8px 15px",
            fontSize: 12.5,
            cursor: "pointer",
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: 999,
              background: ACENTO,
              animation: "telos-breathe 3.4s ease-in-out infinite",
            }}
          />
          <span>{chatOpen ? t.cerrarApoyo : t.ayudaChat}</span>
        </button>
      </header>

      {/* ── Progress stepper ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "clamp(10px,2vw,22px)",
          flexWrap: "wrap",
          padding: "6px clamp(18px,5vw,56px) 0",
          maxWidth: 1080,
          width: "100%",
          margin: "0 auto",
        }}
      >
        {([t.etapa1Label, t.etapa2Label] as const).map((label, i) => {
          const pasoActual = esEvidencia ? 0 : 1;
          return (
            <div
              key={label}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                minWidth: 110,
                flex: 1,
                padding: "2px 0 0",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  fontSize: 9.5,
                  letterSpacing: ".16em",
                  textTransform: "uppercase",
                  color:
                    pasoActual === i ? "#1b1917" : pasoActual > i ? "#8c8478" : "#b7afa4",
                }}
              >
                {label}
              </span>
              <span
                style={{
                  height: 2,
                  width: "100%",
                  background:
                    pasoActual === i ? ACENTO : pasoActual > i ? "#c9bfb0" : "#e4ddd2",
                  transition: "background .5s ease",
                }}
              />
            </div>
          );
        })}
      </div>

      {/* ── Main ── */}
      <main
        style={{
          flex: 1,
          width: "100%",
          maxWidth: 1080,
          margin: "0 auto",
          padding: "clamp(20px,5vh,56px) clamp(18px,5vw,56px) 40px",
          display: "flex",
          flexDirection: "column",
          gap: "clamp(18px,3vh,30px)",
        }}
      >
        {/* Encabezado pregunta */}
        <section
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            maxWidth: 640,
            animation: "telos-fade .5s ease both",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              fontSize: 9.5,
              letterSpacing: ".2em",
              textTransform: "uppercase",
              color: ACENTO,
            }}
          >
            {etapaLabel}
          </span>
          <h2
            style={{
              margin: 0,
              fontFamily: "var(--font-instrument-serif), Georgia, serif",
              fontWeight: 400,
              fontSize: "clamp(26px,3.4vw,42px)",
              lineHeight: 1.13,
            }}
          >
            {titulo}
          </h2>
          <p
            style={{
              margin: 0,
              fontSize: 14.5,
              lineHeight: 1.55,
              color: "#6b6459",
              maxWidth: "48ch",
            }}
          >
            {sub}
          </p>
        </section>

        {error && (
          <p style={{ margin: 0, fontSize: 12.5, color: "#b3261e" }}>{error}</p>
        )}

        {/* Grilla de tarjetas */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 224px), 1fr))",
            gap: "clamp(9px,1.2vw,14px)",
          }}
        >
          {areas.map((a, i) => (
            <button
              key={a.id}
              disabled={guardando}
              onClick={() => setAreaElegida(a.id === areaElegida ? null : a.id)}
              style={{
                position: "relative",
                textAlign: "left",
                display: "flex",
                flexDirection: "column",
                gap: 7,
                minHeight: 88,
                border: `1px solid ${areaElegida === a.id ? ACENTO : "#e6ddd0"}`,
                background:
                  areaElegida === a.id
                    ? `linear-gradient(160deg, rgba(164,85,47,.10), rgba(251,249,246,1) 58%)`
                    : "#fcfaf7",
                borderRadius: 16,
                padding: "16px 17px 18px",
                cursor: guardando ? "default" : "pointer",
                opacity: guardando ? 0.6 : 1,
                animation: "telos-rise .5s ease both",
                animationDelay: `${i * 40}ms`,
                transition: "border-color .25s ease, background .25s ease",
              }}
            >
              <span style={{ fontSize: 15, lineHeight: 1.25 }}>{a.label}</span>
              {areaElegida === a.id && (
                <span
                  style={{
                    position: "absolute",
                    top: 12,
                    right: 14,
                    width: 8,
                    height: 8,
                    borderRadius: 999,
                    background: ACENTO,
                    opacity: 0.8,
                  }}
                />
              )}
            </button>
          ))}
        </div>

        {/* Panel de detalle + confirmar */}
        {areaElegida && (
          <div
            style={{
              display: "flex",
              gap: 12,
              flexWrap: "wrap",
              alignItems: "center",
              border: "1px solid #e2dbd0",
              background: "#fcfaf7",
              borderRadius: 16,
              padding: "14px 16px",
              maxWidth: 680,
              animation: "telos-rise .4s ease both",
            }}
          >
            <input
              value={detalle}
              onChange={(e) => setDetalle(e.target.value)}
              placeholder={t.detallePlaceholder}
              style={{
                flex: 1,
                minWidth: 220,
                border: "none",
                background: "transparent",
                outline: "none",
                fontSize: 14.5,
                color: "#1b1917",
              }}
            />
            <button
              onClick={confirmar}
              disabled={guardando}
              style={{
                border: "1px solid #1b1917",
                background: "#1b1917",
                color: "#f7f4ef",
                borderRadius: 999,
                padding: "11px 22px",
                fontSize: 13,
                cursor: "pointer",
                opacity: guardando ? 0.6 : 1,
              }}
            >
              {guardando ? t.cargando : t.confirmar}
            </button>
          </div>
        )}
      </main>

      {/* ── Panel de chat lateral ── */}
      {chatOpen && (
        <aside
          style={{
            position: "fixed",
            top: 0,
            right: 0,
            bottom: 0,
            width: "min(384px,100%)",
            zIndex: 50,
            background: "#fcfaf7",
            borderLeft: "1px solid #e2dbd0",
            display: "flex",
            flexDirection: "column",
            boxShadow: "-30px 0 60px -50px rgba(27,25,23,.7)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              padding: "16px 18px",
              borderBottom: "1px solid #ece6dc",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <span
                style={{
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  fontSize: 9.5,
                  letterSpacing: ".18em",
                  textTransform: "uppercase",
                  color: ACENTO,
                }}
              >
                {t.apoyoTitulo}
              </span>
              <span style={{ fontSize: 14 }}>{t.apoyoSub}</span>
            </div>
            <button
              onClick={() => setChatOpen(false)}
              style={{
                border: "1px solid #ded7cc",
                background: "transparent",
                color: "#5d564d",
                width: 30,
                height: 30,
                borderRadius: 999,
                cursor: "pointer",
                fontSize: 14,
                lineHeight: 1,
              }}
            >
              ×
            </button>
          </div>

          <div
            style={{
              flex: 1,
              overflow: "auto",
              padding: "16px 18px",
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  maxWidth: "88%",
                  alignSelf: m.who === "me" ? "flex-end" : "flex-start",
                  background: m.who === "me" ? "#1b1917" : "#f4f1ec",
                  color: m.who === "me" ? "#f7f4ef" : "#3b3630",
                  border: `1px solid ${m.who === "me" ? "#1b1917" : "#e8e1d7"}`,
                  borderRadius: 14,
                  padding: "11px 14px",
                  fontSize: 13.5,
                  lineHeight: 1.5,
                }}
              >
                {m.text}
              </div>
            ))}
          </div>

          <div
            style={{
              padding: "10px 18px 16px",
              borderTop: "1px solid #ece6dc",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              {t.sugerencias.map((s) => (
                <button
                  key={s}
                  onClick={() => enviarChat(s)}
                  style={{
                    border: "1px solid #e2dbd0",
                    background: "transparent",
                    color: "#6b6459",
                    borderRadius: 999,
                    padding: "6px 12px",
                    fontSize: 11.5,
                    cursor: "pointer",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
            <div
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                border: "1px solid #e2dbd0",
                borderRadius: 999,
                padding: "6px 6px 6px 14px",
              }}
            >
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") enviarChat(draft);
                }}
                placeholder={t.chatPlaceholder}
                style={{
                  flex: 1,
                  border: "none",
                  background: "transparent",
                  outline: "none",
                  fontSize: 13.5,
                  color: "#1b1917",
                }}
              />
              <button
                onClick={() => enviarChat(draft)}
                style={{
                  border: "none",
                  background: "#1b1917",
                  color: "#f7f4ef",
                  borderRadius: 999,
                  width: 32,
                  height: 32,
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                →
              </button>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
