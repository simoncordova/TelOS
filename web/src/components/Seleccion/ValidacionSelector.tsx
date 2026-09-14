"use client";

import { useEffect, useMemo, useState } from "react";

import { confirmarSeleccion, obtenerCategoriasFase3 } from "@/lib/apiCliente";
import type { AreaVida, Idioma, SeleccionConfirmada } from "@/lib/types";
import { AccionesCuenta } from "../AccionesCuenta";

// Fase 3 -- Coach de Validación. Port fiel de maqueta/fase3/TELOS Fase 3.dc.html.
// Layout: header con logo + stepper de dos pasos como botones de texto,
// main de dos columnas (selector izquierda + constelación SVG derecha),
// tarjetas con chip geométrico + radio + detalle expandible inline.
// Una vez confirmada la 2da etapa el backend devuelve
// `mensaje_apertura_refinado` y la fase pasa a chat (onEntrarRefinado).

const ACENTO = "#a4552f";

// Marcas geométricas para cada tarjeta (radius, rotación) — ciclan sobre las 8 áreas
const MARKS: [string, string][] = [
  ["4px", "0deg"],
  ["999px", "0deg"],
  ["2px", "45deg"],
  ["999px", "0deg"],
  ["4px", "45deg"],
  ["999px", "0deg"],
  ["2px", "0deg"],
  ["4px", "45deg"],
];

const TEXTOS = {
  es: {
    faseLabel: "Fase 3 · Coach de validación",
    cerrarSesion: "Cerrar sesión",
    propositoLabel: "El propósito que vamos a validar",
    kickerEvidencia: "01 · Evidencia pasada",
    kickerFriccion: "02 · Fricción futura",
    tituloEvidencia: "¿En qué área ya viviste este propósito, aunque en pequeño?",
    tituloFriccion: "¿En qué área sería tentador abandonarlo, o chocaría con otra prioridad?",
    subEvidencia: "No hace falta que haya sido perfecto. Basta con una señal real.",
    subFriccion: "No es pesimismo: es tener la respuesta lista de antemano.",
    friccionTransicion: "Ya ocurrió aquí → podría romperse aquí",
    friccionSub: "misma lista, otra pregunta",
    detallePlaceholder: "Contá el momento específico (opcional)",
    siguiente: "Siguiente",
    cargando: "Guardando…",
    volver: "← Volver",
    pickHint: "Elige una o más",
    vizNote: "Las áreas que elijas irán tomando forma aquí.",
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
    cerrarSesion: "Sign out",
    propositoLabel: "The purpose we're going to validate",
    kickerEvidencia: "01 · Past evidence",
    kickerFriccion: "02 · Future friction",
    tituloEvidencia: "In what area have you already lived this purpose, even in a small way?",
    tituloFriccion: "In what area would it be tempting to abandon it, or clash with another priority?",
    subEvidencia: "It doesn't have to have been perfect. A real signal is enough.",
    subFriccion: "This isn't pessimism: it's having the answer ready ahead of time.",
    friccionTransicion: "It already happened here → could break here",
    friccionSub: "same list, different question",
    detallePlaceholder: "Tell the specific moment (optional)",
    siguiente: "Next",
    cargando: "Saving…",
    volver: "← Back",
    pickHint: "Choose one or more",
    vizNote: "The areas you choose will take shape here.",
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

// SVG constelación lateral — muestra qué dimensiones Ikigai tocan las áreas elegidas.
// Las áreas se mapean a dimensiones (L/G/V/N) de forma fija para dar feedback visual
// sin necesitar un endpoint extra.
const AREA_DIMS: Record<string, string[]> = {
  "Trabajo o carrera": ["G", "V"],
  "Work or career": ["G", "V"],
  "Relaciones cercanas": ["L", "N"],
  "Close relationships": ["L", "N"],
  "Un hobby o proyecto personal": ["L", "G"],
  "A hobby or personal project": ["L", "G"],
  "Comunidad o un grupo al que pertenezco": ["N", "V"],
  "Community or a group I belong to": ["N", "V"],
  "Un momento difícil que atravesé": ["G", "N"],
  "A difficult time I went through": ["G", "N"],
  "Una decisión que tomé": ["G", "V"],
  "A decision I made": ["G", "V"],
  "Cómo uso mi tiempo libre": ["L", "G"],
  "How I use my free time": ["L", "G"],
  "Algo que hice sin que nadie me lo pidiera": ["L", "N"],
  "Something I did without anyone asking": ["L", "N"],
};

const DIM_ANGULO: Record<string, number> = { L: -90, N: 0, V: 90, G: 180 };

function ConstellationViz({ picks, acento }: { picks: string[]; acento: string }) {
  const cov = useMemo(() => {
    const out: Record<string, number> = { L: 0, G: 0, V: 0, N: 0 };
    picks.forEach((p) => {
      (AREA_DIMS[p] ?? []).forEach((k) => { out[k] = (out[k] ?? 0) + 1; });
    });
    return out;
  }, [picks]);

  const pol = (r: number, a: number): [number, number] => [
    Math.cos((a * Math.PI) / 180) * r,
    Math.sin((a * Math.PI) / 180) * r,
  ];

  const stage = picks.length === 0 ? 0 : picks.length <= 2 ? 1 : picks.length <= 4 ? 2 : 3;
  const conv = Math.min(1, picks.length / 5);

  const kids: React.ReactNode[] = [];

  kids.push(<circle key="atm" r={214} fill={acento} opacity={0.02 + stage * 0.012} />);
  kids.push(<circle key="atm2" r={214} fill="none" stroke="#1b1917" strokeWidth={0.5} opacity={0.06} />);

  (["L", "N", "V", "G"] as const).forEach((d, i) => {
    const [cx, cy] = pol(66, DIM_ANGULO[d]);
    const c = Math.min(1, (cov[d] ?? 0) / 2);
    kids.push(<circle key={`pt${i}`} cx={cx} cy={cy} r={100} fill={acento} opacity={0.035 + c * 0.105} style={{ transition: "opacity 1s ease" }} />);
    kids.push(<circle key={`po${i}`} cx={cx} cy={cy} r={100} fill="none" stroke={c ? acento : "#c9bfb0"} strokeWidth={c >= 1 ? 1.1 : 0.7} opacity={c ? 0.22 + c * 0.3 : 0.22} strokeDasharray={c ? "none" : "3 8"} />);
  });

  kids.push(<circle key="c1" r={46} fill={acento} opacity={0.04 + conv * 0.16} />);
  kids.push(
    <circle key="c2" r={46 * (0.5 + conv * 0.5)} fill="none" stroke={acento}
      strokeWidth={stage >= 3 ? 1.4 : 0.8} opacity={0.2 + conv * 0.45}
      strokeDasharray={stage >= 3 ? "none" : "14 8"}
      style={{ animation: "telos-breathe 6.5s ease-in-out infinite" }}
    />
  );
  if (stage >= 3) kids.push(<circle key="c3" r={17} fill={acento} opacity={0.3} />);

  return (
    <svg viewBox="-236 -236 472 472" width="100%" height="100%" preserveAspectRatio="xMidYMid meet"
      style={{ position: "absolute", inset: 0, overflow: "visible" }}>
      {kids}
    </svg>
  );
}

export function ValidacionSelector({
  idioma,
  onCambiarIdioma,
  requiereLogin,
  proposito,
  onEntrarRefinado,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  requiereLogin: boolean;
  proposito?: string;
  onEntrarRefinado: (primerMensaje: string) => void;
}) {
  const t = TEXTOS[idioma];
  const [areas, setAreas] = useState<AreaVida[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [etapa, setEtapa] = useState<"evidencia_pasada" | "friccion_futura">("evidencia_pasada");

  // picks: Map de id → detalle (string vacío si sin detalle)
  const [picks, setPicks] = useState<Map<string, string>>(new Map());
  const [abiertos, setAbiertos] = useState<Set<string>>(new Set()); // tarjetas con detalle expandido
  const [guardando, setGuardando] = useState(false);

  const [chatOpen, setChatOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<{ who: "me" | "bot"; text: string }[]>([
    { who: "bot", text: t.mensajeInicialChat },
  ]);

  useEffect(() => {
    let cancelado = false;
    obtenerCategoriasFase3(idioma)
      .then((d) => { if (!cancelado) setAreas(d.areas); })
      .catch(() => { if (!cancelado) setError(t.errorCarga); });
    return () => { cancelado = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idioma]);

  if (error && !areas)
    return <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", padding: 32, textAlign: "center", fontSize: 13.5, color: "#6b6459" }}>{error}</div>;
  if (!areas)
    return <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", fontSize: 13, color: "#a8a096" }}>…</div>;

  const esEvidencia = etapa === "evidencia_pasada";
  const hasPicks = picks.size > 0;

  function togglePick(id: string) {
    if (guardando) return;
    setPicks((prev) => {
      const next = new Map(prev);
      if (next.has(id)) {
        next.delete(id);
        setAbiertos((ab) => { const s = new Set(ab); s.delete(id); return s; });
      } else {
        next.set(id, "");
        // auto-expand el campo de detalle al seleccionar
        setAbiertos((ab) => new Set(ab).add(id));
      }
      return next;
    });
  }

  function setDetalle(id: string, valor: string) {
    setPicks((prev) => { const next = new Map(prev); next.set(id, valor); return next; });
  }

  async function siguiente() {
    if (!hasPicks || guardando) return;
    setGuardando(true);
    setError(null);
    try {
      // Confirma cada área elegida con su detalle
      let ultimoResultado: SeleccionConfirmada | null = null;
      for (const [id, det] of picks.entries()) {
        ultimoResultado = await confirmarSeleccion({
          fase: 3,
          nodoId: id,
          idioma,
          detalleLibre: det.trim() || undefined,
        });
      }
      setPicks(new Map());
      setAbiertos(new Set());
      if (ultimoResultado?.mensaje_apertura_refinado) {
        onEntrarRefinado(ultimoResultado.mensaje_apertura_refinado);
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
    setMessages((prev) => [...prev, { who: "me", text: limpio }, { who: "bot", text: respuesta ?? t.mensajeInicialChat }]);
    setDraft("");
  }

  const picksLabels = areas.filter((a) => picks.has(a.id)).map((a) => a.label);

  return (
    <div style={{
      height: "100%", minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column",
      background: "radial-gradient(70% 45% at 50% 0%, rgba(226,164,74,.12) 0%, rgba(226,164,74,0) 60%), linear-gradient(#fcfaf7 0%, #f5f1ea 55%, #efe8dd 100%)",
      fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
      color: "#1b1917", position: "relative",
    }}>
      <style>{`
        @keyframes telos-rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
        @keyframes telos-fade { from { opacity:0; } to { opacity:1; } }
        @keyframes telos-breathe { 0%,100% { opacity:.5; transform:scale(1); } 50% { opacity:.85; transform:scale(1.04); } }
        .vsel-card:hover { transform: translateY(-2px); }
      `}</style>

      {/* ── Header ── */}
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, padding: "16px clamp(18px,5vw,56px) 8px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/telos-brand.png" alt="TelOS" style={{ width: 32, height: 32, borderRadius: 9, objectFit: "cover", objectPosition: "50% 34%", background: "#1d1b33", flexShrink: 0 }} />
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 12.5, letterSpacing: ".34em", textTransform: "uppercase", color: "#1b1917" }}>Telos</span>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: "#6b6459" }}>{t.faseLabel}</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "clamp(14px,2.4vw,28px)", flexWrap: "wrap" }}>
          {/* Stepper en header — botones de texto con subrayado */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase" }}>
            {([
              { n: "01", label: idioma === "es" ? "Evidencia pasada" : "Past evidence", etapaKey: "evidencia_pasada" },
              { n: "02", label: idioma === "es" ? "Fricción futura" : "Future friction", etapaKey: "friccion_futura" },
            ] as const).map((st) => {
              const activo = etapa === st.etapaKey;
              const completado = st.etapaKey === "evidencia_pasada" && !esEvidencia;
              return (
                <button
                  key={st.n}
                  onClick={() => { if (completado) setEtapa(st.etapaKey); }}
                  style={{
                    display: "flex", alignItems: "baseline", gap: 6,
                    border: "none", background: "transparent", padding: 0,
                    cursor: completado ? "pointer" : "default",
                    color: activo ? "#1b1917" : completado ? "#8c8478" : "#b7afa4",
                    fontFamily: "var(--font-ibm-plex-mono), monospace",
                    fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase",
                  }}
                >
                  <span>{st.n}</span>
                  <span style={{ whiteSpace: "nowrap", borderBottom: `1px solid ${activo ? ACENTO : completado ? "#c9bfb0" : "transparent"}`, paddingBottom: 2 }}>
                    {st.label}
                  </span>
                </button>
              );
            })}
          </div>

          <AccionesCuenta idioma={idioma} onCambiarIdioma={onCambiarIdioma} requiereLogin={requiereLogin} logoutLabel={t.cerrarSesion} />
        </div>
      </header>

      {/* ── Main: 2 columnas ── */}
      <main style={{
        flex: 1, width: "100%", maxWidth: 1240, margin: "0 auto",
        padding: "clamp(16px,4vh,42px) clamp(18px,5vw,56px) clamp(24px,5vh,56px)",
        display: "flex", alignItems: "flex-start", gap: "clamp(20px,4vw,56px)", flexWrap: "wrap",
      }}>

        {/* ── Columna izquierda ── */}
        <div style={{ flex: "1 1 460px", minWidth: "min(100%, 300px)", display: "flex", flexDirection: "column", gap: "clamp(16px,3vh,28px)" }}>

          {/* Propósito a validar */}
          {proposito && (
            <div style={{ display: "flex", flexDirection: "column", gap: 9, maxWidth: 620, borderBottom: "1px solid #e6ddd0", paddingBottom: "clamp(14px,2.5vh,22px)", animation: "telos-fade .5s ease both" }}>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>{t.propositoLabel}</span>
              <p style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(24px,3.2vw,38px)", lineHeight: 1.14, color: "#1b1917" }}>{proposito}</p>
            </div>
          )}

          {/* Kicker + pregunta */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 620, animation: "telos-fade .5s ease both" }}>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: ACENTO }}>
              {esEvidencia ? t.kickerEvidencia : t.kickerFriccion}
            </span>
            <h2 style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontWeight: 400, fontSize: "clamp(21px,2.5vw,30px)", lineHeight: 1.16, color: "#1b1917" }}>
              {esEvidencia ? t.tituloEvidencia : t.tituloFriccion}
            </h2>
            <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.55, color: "#5d564d", maxWidth: "50ch" }}>
              {esEvidencia ? t.subEvidencia : t.subFriccion}
            </p>
          </div>

          {/* Banner transición fricción */}
          {!esEvidencia && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".15em", textTransform: "uppercase", borderTop: "1px solid #e6ddd0", borderBottom: "1px solid #e6ddd0", padding: "9px 0" }}>
              <span style={{ color: "#5d564d" }}>{t.friccionTransicion}</span>
              <span style={{ color: "#6b6459", textTransform: "none", letterSpacing: ".04em" }}>{t.friccionSub}</span>
            </div>
          )}

          {error && <p style={{ margin: 0, fontSize: 12.5, color: "#b3261e" }}>{error}</p>}

          {/* Grilla de tarjetas ricas */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 152px), 1fr))", gap: "clamp(8px,1.1vw,13px)" }}>
            {areas.map((a, i) => {
              const on = picks.has(a.id);
              const open = abiertos.has(a.id) && on;
              const [markRadius, markRot] = MARKS[i % MARKS.length];
              return (
                <div
                  key={a.id}
                  className="vsel-card"
                  style={{
                    display: "flex", flexDirection: "column",
                    border: `1px solid ${on ? ACENTO : "#e6ddd0"}`,
                    background: on ? "linear-gradient(160deg, rgba(164,85,47,.09), rgba(252,250,247,1) 60%)" : "#fcfaf7",
                    borderRadius: 14, overflow: "hidden",
                    transition: "border-color .3s ease, background .3s ease, transform .3s cubic-bezier(.22,.9,.25,1)",
                    animation: "telos-rise .45s ease both",
                    animationDelay: `${i * 45}ms`,
                  }}
                >
                  <button
                    onClick={() => togglePick(a.id)}
                    disabled={guardando}
                    style={{
                      textAlign: "left", display: "flex", flexDirection: "column",
                      justifyContent: "space-between", gap: 16, minHeight: 116,
                      border: "none", background: "transparent",
                      padding: "14px 15px 15px", cursor: guardando ? "default" : "pointer", width: "100%",
                    }}
                  >
                    {/* Top row: chip + radio */}
                    <span style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10, width: "100%" }}>
                      {/* Chip geométrico */}
                      <span style={{
                        width: 34, height: 34, borderRadius: 999,
                        background: on ? "rgba(164,85,47,.14)" : "#f0ece4",
                        flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
                        transition: "background .3s ease",
                      }}>
                        <span style={{
                          width: 12, height: 12,
                          border: `1.5px solid ${on ? ACENTO : "#b7afa4"}`,
                          borderRadius: markRadius,
                          transform: `rotate(${markRot})`,
                          transition: "border-color .3s ease",
                        }} />
                      </span>
                      {/* Radio circular */}
                      <span style={{
                        width: 19, height: 19, borderRadius: 999,
                        border: `1px solid ${on ? ACENTO : "#c9bfb0"}`,
                        background: on ? ACENTO : "transparent",
                        flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
                        transition: "all .28s ease",
                      }}>
                        <span style={{ fontSize: 11, lineHeight: 1, color: "#fcfaf7", opacity: on ? 1 : 0, transition: "opacity .25s ease" }}>✓</span>
                      </span>
                    </span>
                    {/* Label */}
                    <span style={{ display: "flex", flexDirection: "column", gap: 4, width: "100%" }}>
                      <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: 17, lineHeight: 1.18, color: "#1b1917" }}>{a.label}</span>
                      <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".13em", textTransform: "uppercase", color: on ? ACENTO : "#b0a79a" }}>
                        {on ? (esEvidencia ? (idioma === "es" ? "elegida" : "chosen") : (idioma === "es" ? "marcada" : "marked")) : (idioma === "es" ? "toca para elegir" : "tap to choose")}
                      </span>
                    </span>
                  </button>

                  {/* Campo de detalle expandible inline */}
                  {open && (
                    <div style={{ padding: "0 15px 14px", animation: "telos-fade .35s ease both" }}>
                      <input
                        value={picks.get(a.id) ?? ""}
                        onChange={(e) => setDetalle(a.id, e.target.value)}
                        placeholder={a.id in AREA_DIMS
                          ? (esEvidencia
                            ? (idioma === "es" ? "¿Qué momento o contexto concreto?" : "What specific moment or context?")
                            : (idioma === "es" ? "¿Qué lo haría difícil ahí?" : "What would make it hard there?"))
                          : t.detallePlaceholder}
                        style={{
                          width: "100%", border: "none", borderTop: "1px solid #e6ddd0",
                          background: "transparent", outline: "none",
                          fontSize: 13.5, color: "#1b1917", padding: "10px 0 0",
                          fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
                        }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Botones de acción */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", paddingTop: 4 }}>
            <button
              onClick={siguiente}
              disabled={!hasPicks || guardando}
              style={{
                border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef",
                borderRadius: 999, padding: "13px 26px", fontSize: 14, cursor: hasPicks && !guardando ? "pointer" : "default",
                opacity: hasPicks && !guardando ? 1 : 0.45, transition: "all .3s ease",
              }}
            >
              {guardando ? t.cargando : t.siguiente}
            </button>
            {!esEvidencia && (
              <button
                onClick={() => { setEtapa("evidencia_pasada"); setPicks(new Map()); setAbiertos(new Set()); }}
                style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "13px 20px", fontSize: 13, cursor: "pointer" }}
              >
                {t.volver}
              </button>
            )}
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".14em", textTransform: "uppercase", color: "#6b6459" }}>
              {t.pickHint}
            </span>
          </div>
        </div>

        {/* ── Columna derecha: visualización SVG ── */}
        <aside style={{ flex: "1 1 380px", minWidth: "min(100%, 300px)", display: "flex", flexDirection: "column", alignItems: "center", gap: 14, paddingTop: "clamp(0px,2vh,18px)" }}>
          <div style={{ position: "relative", width: "min(100%, 460px)", aspectRatio: "1/1" }}>
            <ConstellationViz picks={picksLabels} acento={ACENTO} />
          </div>
          <p style={{ margin: 0, maxWidth: "34ch", textAlign: "center", fontSize: 12.5, lineHeight: 1.5, color: "#5d564d" }}>
            {t.vizNote}
          </p>
        </aside>
      </main>

      {/* ── Chat lateral ── */}
      {chatOpen && (
        <aside style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(384px,100%)", zIndex: 50, background: "#fcfaf7", borderLeft: "1px solid #e2dbd0", display: "flex", flexDirection: "column", boxShadow: "-30px 0 60px -50px rgba(27,25,23,.7)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "16px 18px", borderBottom: "1px solid #ece6dc" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".18em", textTransform: "uppercase", color: ACENTO }}>{t.apoyoTitulo}</span>
              <span style={{ fontSize: 14 }}>{t.apoyoSub}</span>
            </div>
            <button onClick={() => setChatOpen(false)} style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", width: 30, height: 30, borderRadius: 999, cursor: "pointer", fontSize: 14, lineHeight: 1 }}>×</button>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 12 }}>
            {messages.map((m, i) => (
              <div key={i} style={{ maxWidth: "88%", alignSelf: m.who === "me" ? "flex-end" : "flex-start", background: m.who === "me" ? "#1b1917" : "#f4f1ec", color: m.who === "me" ? "#f7f4ef" : "#3b3630", border: `1px solid ${m.who === "me" ? "#1b1917" : "#e8e1d7"}`, borderRadius: 14, padding: "11px 14px", fontSize: 13.5, lineHeight: 1.5 }}>
                {m.text}
              </div>
            ))}
          </div>
          <div style={{ padding: "10px 18px 16px", borderTop: "1px solid #ece6dc", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              {t.sugerencias.map((s) => (
                <button key={s} onClick={() => enviarChat(s)} style={{ border: "1px solid #e2dbd0", background: "transparent", color: "#6b6459", borderRadius: 999, padding: "6px 12px", fontSize: 11.5, cursor: "pointer" }}>{s}</button>
              ))}
            </div>
            <div style={{ display: "flex", gap: 9, alignItems: "center", border: "1px solid #e2dbd0", background: "#fcfaf7", borderRadius: 999, padding: "7px 7px 7px 18px" }}>
              <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") enviarChat(draft); }} placeholder={t.chatPlaceholder} style={{ flex: 1, minWidth: 0, border: "none", background: "transparent", outline: "none", fontSize: 14.5, color: "#1b1917" }} />
              <button onClick={() => enviarChat(draft)} style={{ border: "none", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, width: 36, height: 36, flexShrink: 0, cursor: "pointer", fontSize: 14 }}>→</button>
            </div>
          </div>
        </aside>
      )}

      {/* Botón flotante de apoyo */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          style={{ position: "fixed", right: "clamp(14px,2.4vw,28px)", bottom: "clamp(14px,2.4vw,28px)", zIndex: 30, display: "flex", alignItems: "center", gap: 9, border: "1px solid #ded7cc", background: "rgba(252,250,247,.8)", color: "#5d564d", borderRadius: 999, padding: "8px 15px", fontSize: 12.5, cursor: "pointer" }}
        >
          <span style={{ width: 7, height: 7, borderRadius: 999, background: ACENTO, animation: "telos-breathe 3.4s ease-in-out infinite" }} />
          <span>{t.ayudaChat}</span>
        </button>
      )}
    </div>
  );
}
