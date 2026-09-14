"use client";

import { useEffect, useMemo, useState } from "react";

import type { Textos } from "@/lib/i18n";
import type { FichaSnapshot } from "@/lib/types";
import { parsearSistema } from "@/lib/parseSistema";

// ─── constants ────────────────────────────────────────────────────────────────

const ACENTO = "#a4552f";
const BG_CARD = "#fcfaf7";
const BORDER = "#e2dbd0";

// Ikigai dimension colors — same as ArbolSelector.tsx
const DIM_COLOR: Record<string, string> = {
  L: "#c8801f",
  G: "#4e4d86",
  V: "#a8532c",
  N: "#3a6d63",
};
const DIM_LABELS_ES: Record<string, string> = { L: "Lo que amás", G: "Lo que el mundo necesita", V: "Lo que hacés bien", N: "Por lo que te pagan" };
const DIM_LABELS_EN: Record<string, string> = { L: "What you love", G: "What the world needs", V: "What you're good at", N: "What you're paid for" };
// Same diagonal angles as ArbolSelector (L=top-left, G=top-right, V=bottom-right, N=bottom-left)
const DIM_ANGULO: Record<string, number> = { L: -135, G: -45, V: 45, N: 135 };

// ─── helpers ──────────────────────────────────────────────────────────────────

/** ISO week key "YYYY-Www" — same week same key, stable across page reloads */
function isoWeekKey(date: Date = new Date()): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const year = d.getUTCFullYear();
  const week = Math.ceil(((d.getTime() - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7);
  return `${year}-W${String(week).padStart(2, "0")}`;
}

/** localStorage key scoped to user + week so resets automatically each week */
function storageKey(usuarioId: string): string {
  return `telos:ejecuciones:${usuarioId}:${isoWeekKey()}`;
}

/**
 * Parse a rough frequency number out of the "Cuándo/dónde" / "When/where"
 * value from the sistema string. Handles the most common patterns the
 * SistemaSelector taxonomy produces:
 *   "3 veces a la semana" / "3 times a week"  → 3
 *   "diario" / "daily" / "todos los días"     → 7
 *   "una vez a la semana" / "once a week"      → 1
 *   "5 veces" etc.                             → 5
 * Returns null if nothing is recognizable — caller shows "—" gracefully.
 */
function parsearFrecuencia(cuandoDonde: string): number | null {
  const s = cuandoDonde.toLowerCase();

  // "daily" / "diario" / "every day" / "todos los días"
  if (/\b(diario|daily|cada día|every day|todos los días)\b/.test(s)) return 7;

  // "once a week" / "una vez a la semana"
  if (/\b(once a week|una vez a la semana|1 vez a la semana|1 time a week)\b/.test(s)) return 1;

  // "N times a week" / "N veces a la semana"
  const mEN = s.match(/(\d+)\s+times?\s+a\s+week/);
  if (mEN) return parseInt(mEN[1], 10);
  const mES = s.match(/(\d+)\s+veces?\s+a\s+la\s+semana/);
  if (mES) return parseInt(mES[1], 10);

  // bare "N veces" / "N times"
  const mBare = s.match(/(\d+)\s+veces?|(\d+)\s+times?/);
  if (mBare) return parseInt(mBare[1] ?? mBare[2], 10);

  return null;
}

// ─── SVG helpers (same conventions as ArbolSelector) ─────────────────────────

function toRad(deg: number) { return (deg * Math.PI) / 180; }
function polar(r: number, deg: number): [number, number] {
  return [Math.cos(toRad(deg)) * r, Math.sin(toRad(deg)) * r];
}
function arcPath(r: number, a0: number, a1: number): string {
  if (Math.abs(a1 - a0) >= 360) return `M ${r},0 A ${r},${r} 0 1 1 ${r - 0.001},0 Z`;
  const [x0, y0] = polar(r, a0);
  const [x1, y1] = polar(r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
}

// ─── sub-components ───────────────────────────────────────────────────────────

/** Circular compliance arc + centre number */
function RingChart({
  n,
  total,
  label,
  sublabel,
}: {
  n: number;
  total: number;
  label: string;    // e.g. "3 de 5 veces"
  sublabel: string; // e.g. "Esta semana"
}) {
  const pct = total > 0 ? Math.min(1, n / total) : 0;
  const R = 52;
  const STROKE = 7;
  const deg = pct * 360;
  // trail arc (full circle)
  const trailD = arcPath(R, -90, 269.9);
  // fill arc
  const fillD = deg > 0 ? arcPath(R, -90, -90 + deg) : null;
  const pctInt = Math.round(pct * 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <div style={{ position: "relative", width: (R + STROKE + 2) * 2, height: (R + STROKE + 2) * 2 }}>
        <svg
          width={(R + STROKE + 2) * 2}
          height={(R + STROKE + 2) * 2}
          viewBox={`${-(R + STROKE + 2)} ${-(R + STROKE + 2)} ${(R + STROKE + 2) * 2} ${(R + STROKE + 2) * 2}`}
          aria-hidden="true"
        >
          {/* background ring */}
          <path d={trailD} fill="none" stroke="#ede5d8" strokeWidth={STROKE} strokeLinecap="round" />
          {/* fill arc */}
          {fillD && (
            <path
              d={fillD}
              fill="none"
              stroke={pct >= 1 ? "#3a6d63" : ACENTO}
              strokeWidth={STROKE}
              strokeLinecap="round"
              style={{ transition: "stroke-dashoffset .6s ease" }}
            />
          )}
        </svg>
        {/* centre text */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-instrument-serif), Georgia, serif",
              fontSize: 26,
              lineHeight: 1,
              color: pct >= 1 ? "#3a6d63" : "#1b1917",
            }}
          >
            {pctInt}%
          </span>
        </div>
      </div>
      <span
        style={{
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 11,
          letterSpacing: ".1em",
          textTransform: "uppercase",
          color: "#6b6459",
          textAlign: "center",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "var(--font-ibm-plex-mono), monospace",
          fontSize: 9,
          letterSpacing: ".14em",
          textTransform: "uppercase",
          color: "#a8a096",
          textAlign: "center",
        }}
      >
        {sublabel}
      </span>
    </div>
  );
}

/** Static decorative ikigai radial — 4 labelled circles at the diagonals */
function IkigaiDecorative({ idioma }: { idioma: "es" | "en" }) {
  const labels = idioma === "en" ? DIM_LABELS_EN : DIM_LABELS_ES;
  const dims = ["L", "G", "V", "N"] as const;
  const SIZE = 260;
  const HALF = SIZE / 2;
  const R_BLOB = 80;
  const R_POS = 80;

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      aria-hidden="true"
      style={{ display: "block", overflow: "visible" }}
    >
      {/* center convergence glow */}
      <circle cx={HALF} cy={HALF} r={28} fill={ACENTO} opacity={0.12} />
      <circle cx={HALF} cy={HALF} r={18} fill={ACENTO} opacity={0.18} />
      <circle cx={HALF} cy={HALF} r={9}  fill={ACENTO} opacity={0.7} />

      {dims.map((d) => {
        const ang = DIM_ANGULO[d];
        const color = DIM_COLOR[d];
        const [bx, by] = polar(R_POS, ang);
        const [lx, ly] = polar(R_POS + 54, ang);

        // line from blob to center
        return (
          <g key={d} transform={`translate(${HALF},${HALF})`}>
            {/* connector line */}
            <line
              x1={Math.cos(toRad(ang)) * 12}
              y1={Math.sin(toRad(ang)) * 12}
              x2={Math.cos(toRad(ang)) * (R_POS - R_BLOB * 0.35)}
              y2={Math.sin(toRad(ang)) * (R_POS - R_BLOB * 0.35)}
              stroke={color}
              strokeWidth={1}
              opacity={0.28}
            />
            {/* blob */}
            <circle cx={bx} cy={by} r={R_BLOB * 0.38} fill={color} opacity={0.13} />
            <circle cx={bx} cy={by} r={R_BLOB * 0.22} fill={color} opacity={0.2} />
            <circle cx={bx} cy={by} r={4} fill={color} opacity={0.9} />
            {/* label */}
            <text
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={color}
              fontSize={9}
              fontFamily="var(--font-ibm-plex-mono), monospace"
              letterSpacing={0.8}
              opacity={0.85}
            >
              {labels[d].toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** The 4-cell system flow diagram, rebuilt from parsed sistema rows */
function SistemaFlowDiagram({
  filas,
  t,
  idioma,
  proposito,
}: {
  filas: [string, string][];
  t: Textos;
  idioma: "es" | "en";
  proposito: string | undefined;
}) {
  // Map parsed rows by normalised label key
  const byKey = useMemo(() => {
    const map: Record<string, string> = {};
    for (const [label, valor] of filas) {
      const k = label.toLowerCase().replace(/[^a-záéíóúüñ/]/g, "");
      map[k] = valor;
    }
    return map;
  }, [filas]);

  const accion  = byKey["acción"]    ?? byKey["accion"]  ?? byKey["action"] ?? "—";
  const cuando  = byKey["cuándodónde"] ?? byKey["cuandodónde"] ?? byKey["cuandodonde"] ?? byKey["whenwhere"] ?? "—";
  const metrica = byKey["métrica"]   ?? byKey["metrica"] ?? byKey["metric"] ?? "—";
  const obstaculo = byKey["obstáculo"] ?? byKey["obstaculo"] ?? byKey["obstacle"] ?? "—";

  const labelColor = "#6b6459";
  const cellStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 5,
    textAlign: "center",
    flex: "1 1 140px",
    minWidth: 120,
  };
  const kicStyle: React.CSSProperties = {
    fontFamily: "var(--font-ibm-plex-mono), monospace",
    fontSize: 9,
    letterSpacing: ".18em",
    textTransform: "uppercase",
    color: labelColor,
  };
  const valStyle: React.CSSProperties = {
    fontFamily: "var(--font-instrument-serif), Georgia, serif",
    fontSize: "clamp(15px,1.8vw,19px)",
    lineHeight: 1.22,
    color: "#1b1917",
  };

  const divider = (
    <div style={{ width: "clamp(18px,3vw,40px)", height: 1, background: "#d8cfc2", flex: "none" }} />
  );

  void t; void idioma; // used via prop type only

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "clamp(12px,2vh,20px)" }}>
      {/* top: cuándo/dónde */}
      <div style={{ ...cellStyle }}>
        <span style={kicStyle}>{filas.find(([l]) => /cuándo|cuando|when/i.test(l))?.[0] ?? (idioma === "en" ? "When/where" : "Cuándo/dónde")}</span>
        <span style={valStyle}>{cuando}</span>
      </div>

      <div style={{ width: 1, height: "clamp(14px,2.5vh,26px)", background: "#d8cfc2" }} />

      {/* middle row: acción — [purpose circle] — métrica */}
      <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap", justifyContent: "center" }}>
        <div style={{ ...cellStyle }}>
          <span style={kicStyle}>{filas.find(([l]) => /acci[oó]n|action/i.test(l))?.[0] ?? (idioma === "en" ? "Action" : "Acción")}</span>
          <span style={valStyle}>{accion}</span>
        </div>

        {divider}

        {/* centre circle */}
        <div
          style={{
            flex: "none",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 7,
            textAlign: "center",
            width: "clamp(150px,18vw,200px)",
            aspectRatio: "1 / 1",
            border: `1px solid #ddd3c5`,
            borderRadius: "50%",
            background: `radial-gradient(70% 70% at 50% 40%, rgba(164,85,47,.10) 0%, ${BG_CARD} 72%)`,
            padding: 16,
          }}
        >
          <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 8.5, letterSpacing: ".22em", textTransform: "uppercase", color: ACENTO }}>
            {idioma === "en" ? "Your system" : "Tu sistema"}
          </span>
          {proposito && (
            <span style={{ fontSize: 11.5, lineHeight: 1.4, color: "#5d564d" }}>{proposito}</span>
          )}
        </div>

        {divider}

        <div style={{ ...cellStyle }}>
          <span style={kicStyle}>{filas.find(([l]) => /m[eé]trica|metric/i.test(l))?.[0] ?? (idioma === "en" ? "Metric" : "Métrica")}</span>
          <span style={valStyle}>{metrica}</span>
        </div>
      </div>

      <div style={{ width: 1, height: "clamp(14px,2.5vh,26px)", background: "linear-gradient(#d8cfc2, #cdbfa9)" }} />

      {/* bottom: obstáculo */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 7,
          textAlign: "center",
          border: "1px dashed #cdbfa9",
          borderRadius: 16,
          padding: "14px 20px 16px",
          maxWidth: 380,
          background: "rgba(252,250,247,.7)",
        }}
      >
        <span style={kicStyle}>{filas.find(([l]) => /obst[áa]culo|obstacle/i.test(l))?.[0] ?? (idioma === "en" ? "Obstacle" : "Obstáculo")}</span>
        <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(13px,1.5vw,16px)", lineHeight: 1.3, color: "#6b6459" }}>
          {obstaculo}
        </span>
      </div>
    </div>
  );
}

// ─── main export ──────────────────────────────────────────────────────────────

export function SustainView({
  t,
  idioma,
  usuarioId,
  ficha,
}: {
  t: Textos;
  idioma: "es" | "en";
  usuarioId: string;
  ficha: FichaSnapshot;
}) {
  const datos = (ficha.actual?.datos ?? {}) as { proposito?: string; sistema?: string };
  const proposito = datos.proposito;
  const sistema   = datos.sistema;
  const filasSistema = sistema ? parsearSistema(sistema) : [];

  // --- execution tracking (localStorage, resets each ISO week) ---
  const [ejecuciones, setEjecuciones] = useState(0);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey(usuarioId));
      if (stored) setEjecuciones(parseInt(stored, 10) || 0);
    } catch { /* SSR / private browsing */ }
  }, [usuarioId]);

  function registrarEjecucion() {
    const next = ejecuciones + 1;
    setEjecuciones(next);
    setFlash(true);
    setTimeout(() => setFlash(false), 1200);
    try {
      localStorage.setItem(storageKey(usuarioId), String(next));
    } catch { /* SSR / private browsing */ }
  }

  // --- frequency from cuando_donde ---
  const cuandoValor = filasSistema.find(([l]) => /cuándo|cuando|when/i.test(l))?.[1] ?? "";
  const frecuencia = parsearFrecuencia(cuandoValor);

  // --- compliance for this week ---
  const cumplimientoLabel = frecuencia != null
    ? t.sustain_cumplimiento_veces
        .replace("{n}", String(Math.min(ejecuciones, frecuencia)))
        .replace("{total}", String(frecuencia))
    : t.sustain_sin_frecuencia;

  const cardStyle: React.CSSProperties = {
    border: `1px solid ${BORDER}`,
    background: BG_CARD,
    borderRadius: 20,
    padding: "20px 22px",
    display: "flex",
    flexDirection: "column",
    gap: 16,
  };

  const kicker: React.CSSProperties = {
    margin: 0,
    fontFamily: "var(--font-ibm-plex-mono), monospace",
    fontSize: 9.5,
    letterSpacing: ".16em",
    textTransform: "uppercase" as const,
    color: "#6b6459",
  };

  return (
    <div
      style={{
        margin: "12px 16px 0",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      {/* ── 1. PROPÓSITO ─────────────────────────────────────────────────── */}
      {proposito && (
        <div style={cardStyle}>
          <h2 style={kicker}>{t.sustain_proposito_kicker}</h2>
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-instrument-serif), Georgia, serif",
              fontSize: "clamp(20px,2.6vw,30px)",
              lineHeight: 1.22,
              color: "#1b1917",
            }}
          >
            {proposito}
          </p>
        </div>
      )}

      {/* ── 2. SISTEMA FLOW DIAGRAM + EXECUTION BUTTON + RING ────────────── */}
      {filasSistema.length > 0 && (
        <div style={{ ...cardStyle, gap: 20 }}>
          <h2 style={kicker}>{t.sustain_sistema_kicker}</h2>

          <SistemaFlowDiagram
            filas={filasSistema}
            t={t}
            idioma={idioma}
            proposito={proposito}
          />

          {/* divider */}
          <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 18, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
            {/* execution button */}
            <button
              type="button"
              onClick={registrarEjecucion}
              style={{
                border: `1.5px solid ${flash ? "#3a6d63" : "#1b1917"}`,
                background: flash ? "#3a6d63" : "#1b1917",
                color: "#f7f4ef",
                borderRadius: 999,
                padding: "13px 26px",
                fontSize: 14,
                fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
                cursor: "pointer",
                transition: "background .3s ease, border-color .3s ease",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span style={{ fontSize: 16, lineHeight: 1 }}>✓</span>
              {flash ? t.sustain_ejecutado_registrado : t.sustain_ejecutado_boton}
            </button>

            {/* compliance ring */}
            {frecuencia != null && (
              <RingChart
                n={Math.min(ejecuciones, frecuencia)}
                total={frecuencia}
                label={cumplimientoLabel}
                sublabel={t.sustain_periodo_semana}
              />
            )}

            {frecuencia == null && ejecuciones > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                <span style={{ ...kicker, fontSize: 9 }}>{t.sustain_cumplimiento_kicker}</span>
                <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: 22, color: "#1b1917" }}>{ejecuciones}×</span>
                <span style={{ ...kicker, fontSize: 8, color: "#a8a096" }}>{t.sustain_periodo_semana}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 3. IKIGAI SECTION ────────────────────────────────────────────── */}
      <div style={{ ...cardStyle, flexDirection: "row", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
        <IkigaiDecorative idioma={idioma} />
        <div style={{ flex: "1 1 180px", display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={kicker}>{t.sustain_descubrir_kicker}</h2>
          <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: "#5d564d" }}>
            {t.sustain_descubrir_desc}
          </p>
          {proposito && (
            <p
              style={{
                margin: 0,
                fontFamily: "var(--font-instrument-serif), Georgia, serif",
                fontSize: "clamp(15px,1.8vw,19px)",
                lineHeight: 1.3,
                color: "#1b1917",
                borderLeft: `2px solid ${ACENTO}`,
                paddingLeft: 12,
              }}
            >
              {proposito}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
