"use client";

import { useEffect, useMemo, useState } from "react";

import type { Textos } from "@/lib/i18n";
import type { FichaSnapshot, FichaVersion } from "@/lib/types";
import { parsearSistema } from "@/lib/parseSistema";

// ─── constants ────────────────────────────────────────────────────────────────

const ACENTO = "#a4552f";
const BG_CARD = "#fcfaf7";
const BORDER = "#e2dbd0";

// Ikigai dimension colors + angles — identical to ArbolSelector.tsx
const DIM_COLOR: Record<string, string> = {
  L: "#c8801f",
  G: "#4e4d86",
  V: "#a8532c",
  N: "#3a6d63",
};
const DIM_ANGULO: Record<string, number> = { L: -135, G: -45, V: 45, N: 135 };
const DIM_ORDER = ["L", "G", "V", "N"] as const;
const DIM_LABELS_ES: Record<string, string> = {
  L: "Lo que amás",
  G: "Lo que el mundo necesita",
  V: "Lo que hacés bien",
  N: "Por lo que te pagan",
};
const DIM_LABELS_EN: Record<string, string> = {
  L: "What you love",
  G: "What the world needs",
  V: "What you're good at",
  N: "What you're paid for",
};

// ─── types ────────────────────────────────────────────────────────────────────

type IkigaiDatos = {
  cobertura: Record<string, number>; // { L: 2, G: 1, V: 3, N: 0 }
  selecciones: { hojaLabel: string; dims: string[] }[];
  valores: string[];
};

// ─── helpers ──────────────────────────────────────────────────────────────────

/** Extract ikigai data from the first FichaVersion that has it (fase 1 close). */
function extractIkigai(historial: FichaVersion[], actual: FichaVersion | null): IkigaiDatos | null {
  // Search newest-first — most recent fase-1 version has the correct data
  const versions = actual ? [...historial, actual] : [...historial];
  for (const v of [...versions].reverse()) {
    const d = v.datos as Record<string, unknown>;
    if (d.cobertura_ikigai && typeof d.cobertura_ikigai === "object") {
      return {
        cobertura: d.cobertura_ikigai as Record<string, number>,
        selecciones: (d.selecciones_ikigai as { hojaLabel: string; dims: string[] }[] | undefined) ?? [],
        valores: (d.valores_ikigai as string[] | undefined) ?? [],
      };
    }
  }
  return null;
}

/** ISO week key "YYYY-Www" */
function isoWeekKey(date: Date = new Date()): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const year = d.getUTCFullYear();
  const week = Math.ceil(((d.getTime() - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7);
  return `${year}-W${String(week).padStart(2, "0")}`;
}

function storageKey(usuarioId: string): string {
  return `telos:ejecuciones:${usuarioId}:${isoWeekKey()}`;
}

function parsearFrecuencia(cuandoDonde: string): number | null {
  const s = cuandoDonde.toLowerCase();
  if (/\b(diario|daily|cada día|every day|todos los días)\b/.test(s)) return 7;
  if (/\b(once a week|una vez a la semana|1 vez a la semana|1 time a week)\b/.test(s)) return 1;
  const mEN = s.match(/(\d+)\s+times?\s+a\s+week/);
  if (mEN) return parseInt(mEN[1], 10);
  const mES = s.match(/(\d+)\s+veces?\s+a\s+la\s+semana/);
  if (mES) return parseInt(mES[1], 10);
  const mBare = s.match(/(\d+)\s+veces?|(\d+)\s+times?/);
  if (mBare) return parseInt(mBare[1] ?? mBare[2], 10);
  return null;
}

// ─── SVG helpers ──────────────────────────────────────────────────────────────

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
function sectorPath(ri: number, ro: number, a0: number, a1: number): string {
  const [xi0, yi0] = polar(ri, a0);
  const [xi1, yi1] = polar(ri, a1);
  const [xo0, yo0] = polar(ro, a0);
  const [xo1, yo1] = polar(ro, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${xi0} ${yi0} L ${xo0} ${yo0} A ${ro} ${ro} 0 ${large} 1 ${xo1} ${yo1} L ${xi1} ${yi1} A ${ri} ${ri} 0 ${large} 0 ${xi0} ${yi0} Z`;
}

// ─── sub-components ───────────────────────────────────────────────────────────

/** Full real ikigai chart using stored cobertura + selecciones. */
function IkigaiChart({
  ikigai,
  idioma,
}: {
  ikigai: IkigaiDatos;
  idioma: "es" | "en";
}) {
  const labels = idioma === "en" ? DIM_LABELS_EN : DIM_LABELS_ES;
  const { cobertura, selecciones, valores } = ikigai;
  const SIZE = 300;
  const HALF = SIZE / 2;

  // Compute overall convergence (0–1) from coverage
  const conv = DIM_ORDER.reduce(
    (acc, d) => acc + Math.min(1, (cobertura[d] ?? 0) / 3),
    0
  ) / DIM_ORDER.length;

  // Position nodes in polar space by their dims vector (same logic as ArbolSelector)
  const nodosPosicionados = useMemo(() => {
    return selecciones.map((n, i) => {
      let x = 0; let y = 0;
      (n.dims || []).forEach((k) => {
        const a = toRad(DIM_ANGULO[k] ?? 0);
        x += Math.cos(a); y += Math.sin(a);
      });
      let ang = Math.atan2(y, x);
      ang += ((i % 3) - 1) * 0.3;
      const w = n.dims?.length ?? 1;
      const ca = Math.abs(Math.cos(ang));
      const sa = Math.abs(Math.sin(ang));
      const clear = Math.min(88, Math.max(56 / Math.max(ca, 0.001), 48 / Math.max(sa, 0.001)));
      const r = Math.min(88, Math.max(clear + 6, 80 - w * 4 + (i % 2) * 4));
      return { n, w, x: Math.cos(ang) * r, y: Math.sin(ang) * r };
    });
  }, [selecciones]);

  return (
    <svg
      width={SIZE}
      height={SIZE}
      viewBox={`${-HALF} ${-HALF} ${SIZE} ${SIZE}`}
      aria-label={idioma === "en" ? "Your Ikigai map" : "Tu mapa Ikigai"}
      style={{ display: "block", overflow: "visible", flexShrink: 0 }}
    >
      {/* reference rings */}
      {[88, 66, 44, 22].map((r, i) => (
        <circle key={`ref${i}`} r={r} fill="none" stroke="#1b1917" strokeWidth={0.4} opacity={0.07} />
      ))}

      {/* dimension sectors + arcs */}
      {DIM_ORDER.map((d) => {
        const ang = DIM_ANGULO[d];
        const color = DIM_COLOR[d];
        const cov = Math.min(1, (cobertura[d] ?? 0) / 3);
        const a0 = ang - 43; const a1 = ang + 43;
        const listo = cov >= 1;
        return (
          <g key={d}>
            {/* filled sector, scales with coverage */}
            <path
              d={sectorPath(18, 36 + cov * 46, a0, a1)}
              fill={color}
              opacity={0.06 + cov * 0.18}
            />
            {/* outer track */}
            <path d={arcPath(86, a0, a1)} fill="none" stroke={color} strokeWidth={0.8} opacity={0.15} strokeLinecap="round" />
            {/* filled arc */}
            {cov > 0 && (
              <path
                d={arcPath(86, a0, a0 + (a1 - a0) * cov)}
                fill="none"
                stroke={color}
                strokeWidth={listo ? 2.8 : 1.8}
                opacity={listo ? 0.95 : 0.6}
                strokeLinecap="round"
              />
            )}
            {/* dimension dot + label */}
            {(() => {
              const [ax, ay] = polar(57, ang);
              const [lx, ly] = polar(98, ang);
              return (
                <>
                  <circle cx={ax} cy={ay} r={14 + cov * 10} fill={color} opacity={0.06 + cov * 0.12} />
                  <circle cx={ax} cy={ay} r={3} fill={cov ? color : "#c3bab0"} opacity={cov ? 1 : 0.5} />
                  <text
                    x={lx}
                    y={ly + (ay < 0 ? -7 : 13)}
                    textAnchor="middle"
                    fill={cov ? color : "#a8a096"}
                    fontSize={8.5}
                    fontFamily="var(--font-ibm-plex-mono), monospace"
                    letterSpacing={1.2}
                  >
                    {labels[d].toUpperCase()}
                  </text>
                  {/* pct label */}
                  {cov > 0 && (() => {
                    const [px, py] = polar(48 + cov * 20, ang);
                    return (
                      <text
                        x={px} y={py + 3.5}
                        textAnchor="middle"
                        fill={color}
                        opacity={listo ? 0.9 : 0.6}
                        fontSize={listo ? 9 : 8}
                        fontFamily="var(--font-ibm-plex-mono), monospace"
                        letterSpacing={0.8}
                      >
                        {Math.round(cov * 100)}%
                      </text>
                    );
                  })()}
                </>
              );
            })()}
          </g>
        );
      })}

      {/* valores ring */}
      {valores.length > 0 && (
        <circle
          r={92}
          fill="none"
          stroke="#4e4d86"
          strokeWidth={0.9}
          opacity={0.2 + valores.length * 0.08}
          strokeDasharray={valores.length >= 3 ? "none" : "18 7"}
        />
      )}

      {/* selection node dots */}
      {nodosPosicionados.map((p, i) => {
        const nc = (p.w ?? 1) >= 3 ? ACENTO : DIM_COLOR[p.n.dims?.[0] ?? ""] ?? ACENTO;
        return (
          <g key={i}>
            {(p.n.dims || []).map((k, j) => {
              const [ax, ay] = polar(57, DIM_ANGULO[k] ?? 0);
              return (
                <line
                  key={j}
                  x1={p.x} y1={p.y}
                  x2={ax} y2={ay}
                  stroke={DIM_COLOR[k] ?? "#aaa"}
                  strokeWidth={0.7}
                  opacity={0.14 + (p.w ?? 1) * 0.06}
                />
              );
            })}
            <circle cx={p.x} cy={p.y} r={3 + (p.w ?? 1) * 1.2} fill={nc} opacity={0.12} />
            <circle cx={p.x} cy={p.y} r={2 + (p.w ?? 1) * 0.5} fill={nc} opacity={0.9} />
            <text
              x={p.x} y={p.y - (7 + (p.w ?? 1) * 3)}
              textAnchor="middle"
              fill="#2c2823"
              fontSize={(p.w ?? 1) >= 3 ? 9.5 : 8.5}
              fontFamily="var(--font-instrument-sans), sans-serif"
              opacity={(p.w ?? 1) >= 3 ? 0.9 : 0.65}
            >
              {p.n.hojaLabel}
            </text>
          </g>
        );
      })}

      {/* center convergence glow */}
      <circle r={26} fill={ACENTO} opacity={0.03 + conv * 0.06} />
      <circle r={16} fill={ACENTO} opacity={0.05 + conv * 0.22} />
      <circle r={conv > 0 ? 20 * (0.45 + conv * 0.55) : 6} fill={ACENTO} opacity={0.65} />
    </svg>
  );
}

/** Fallback purely decorative chart for old fichas without stored ikigai data. */
function IkigaiDecorative({ idioma }: { idioma: "es" | "en" }) {
  const labels = idioma === "en" ? DIM_LABELS_EN : DIM_LABELS_ES;
  const SIZE = 260; const HALF = SIZE / 2; const R_POS = 80;
  return (
    <svg
      width={SIZE} height={SIZE}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      aria-hidden="true"
      style={{ display: "block", overflow: "visible", flexShrink: 0 }}
    >
      <circle cx={HALF} cy={HALF} r={28} fill={ACENTO} opacity={0.12} />
      <circle cx={HALF} cy={HALF} r={18} fill={ACENTO} opacity={0.18} />
      <circle cx={HALF} cy={HALF} r={9}  fill={ACENTO} opacity={0.7} />
      {DIM_ORDER.map((d) => {
        const ang = DIM_ANGULO[d];
        const color = DIM_COLOR[d];
        const [bx, by] = polar(R_POS, ang);
        const [lx, ly] = polar(R_POS + 54, ang);
        return (
          <g key={d} transform={`translate(${HALF},${HALF})`}>
            <line
              x1={Math.cos(toRad(ang)) * 12} y1={Math.sin(toRad(ang)) * 12}
              x2={Math.cos(toRad(ang)) * (R_POS - 28)} y2={Math.sin(toRad(ang)) * (R_POS - 28)}
              stroke={color} strokeWidth={1} opacity={0.28}
            />
            <circle cx={bx} cy={by} r={30} fill={color} opacity={0.13} />
            <circle cx={bx} cy={by} r={18} fill={color} opacity={0.2} />
            <circle cx={bx} cy={by} r={4}  fill={color} opacity={0.9} />
            <text
              x={lx} y={ly} textAnchor="middle" dominantBaseline="middle"
              fill={color} fontSize={9}
              fontFamily="var(--font-ibm-plex-mono), monospace"
              letterSpacing={0.8} opacity={0.85}
            >
              {labels[d].toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Compliance ring arc + % label */
function RingChart({
  n, total, label, sublabel,
}: {
  n: number; total: number; label: string; sublabel: string;
}) {
  const pct = total > 0 ? Math.min(1, n / total) : 0;
  const R = 52; const STROKE = 7;
  const trailD = arcPath(R, -90, 269.9);
  const fillD = pct > 0 ? arcPath(R, -90, -90 + pct * 360) : null;
  const W = (R + STROKE + 2) * 2;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      <div style={{ position: "relative", width: W, height: W }}>
        <svg width={W} height={W}
          viewBox={`${-(R + STROKE + 2)} ${-(R + STROKE + 2)} ${W} ${W}`}
          aria-hidden="true"
        >
          <path d={trailD} fill="none" stroke="#ede5d8" strokeWidth={STROKE} strokeLinecap="round" />
          {fillD && (
            <path d={fillD} fill="none"
              stroke={pct >= 1 ? "#3a6d63" : ACENTO}
              strokeWidth={STROKE} strokeLinecap="round"
            />
          )}
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          pointerEvents: "none",
        }}>
          <span style={{
            fontFamily: "var(--font-instrument-serif), Georgia, serif",
            fontSize: 26, lineHeight: 1,
            color: pct >= 1 ? "#3a6d63" : "#1b1917",
          }}>
            {Math.round(pct * 100)}%
          </span>
        </div>
      </div>
      <span style={{
        fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 11,
        letterSpacing: ".1em", textTransform: "uppercase", color: "#6b6459", textAlign: "center",
      }}>{label}</span>
      <span style={{
        fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9,
        letterSpacing: ".14em", textTransform: "uppercase", color: "#a8a096", textAlign: "center",
      }}>{sublabel}</span>
    </div>
  );
}

/** System flow diagram reconstructed from parsearSistema rows */
function SistemaFlowDiagram({
  filas, idioma, proposito,
}: {
  filas: [string, string][]; idioma: "es" | "en"; proposito: string | undefined;
}) {
  const byKey = useMemo(() => {
    const m: Record<string, string> = {};
    for (const [l, v] of filas) m[l.toLowerCase().replace(/[^a-záéíóúüñ/]/g, "")] = v;
    return m;
  }, [filas]);

  const accion    = byKey["acción"]     ?? byKey["accion"]    ?? byKey["action"]    ?? "—";
  const cuando    = byKey["cuándodónde"]?? byKey["cuandodonde"]?? byKey["whenwhere"] ?? "—";
  const metrica   = byKey["métrica"]    ?? byKey["metrica"]   ?? byKey["metric"]    ?? "—";
  const obstaculo = byKey["obstáculo"]  ?? byKey["obstaculo"] ?? byKey["obstacle"]  ?? "—";

  const kic: React.CSSProperties = {
    fontFamily: "var(--font-ibm-plex-mono), monospace",
    fontSize: 9, letterSpacing: ".18em", textTransform: "uppercase", color: "#6b6459",
  };
  const val: React.CSSProperties = {
    fontFamily: "var(--font-instrument-serif), Georgia, serif",
    fontSize: "clamp(15px,1.8vw,19px)", lineHeight: 1.22, color: "#1b1917",
  };
  const cell: React.CSSProperties = {
    display: "flex", flexDirection: "column", alignItems: "center",
    gap: 5, textAlign: "center", flex: "1 1 130px", minWidth: 110,
  };
  const div = <div style={{ width: "clamp(16px,3vw,36px)", height: 1, background: "#d8cfc2", flex: "none" }} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "clamp(10px,2vh,18px)" }}>
      <div style={cell}>
        <span style={kic}>{filas.find(([l]) => /cuándo|cuando|when/i.test(l))?.[0] ?? (idioma === "en" ? "When/where" : "Cuándo/dónde")}</span>
        <span style={val}>{cuando}</span>
      </div>
      <div style={{ width: 1, height: "clamp(12px,2vh,22px)", background: "#d8cfc2" }} />
      <div style={{ display: "flex", alignItems: "center", gap: 0, flexWrap: "wrap", justifyContent: "center" }}>
        <div style={cell}>
          <span style={kic}>{filas.find(([l]) => /acci[oó]n|action/i.test(l))?.[0] ?? (idioma === "en" ? "Action" : "Acción")}</span>
          <span style={val}>{accion}</span>
        </div>
        {div}
        <div style={{
          flex: "none", display: "flex", flexDirection: "column", alignItems: "center",
          justifyContent: "center", gap: 7, textAlign: "center",
          width: "clamp(140px,16vw,190px)", aspectRatio: "1/1",
          border: "1px solid #ddd3c5", borderRadius: "50%",
          background: `radial-gradient(70% 70% at 50% 40%, rgba(164,85,47,.10) 0%, ${BG_CARD} 72%)`,
          padding: 14,
        }}>
          <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 8, letterSpacing: ".22em", textTransform: "uppercase", color: ACENTO }}>
            {idioma === "en" ? "Your system" : "Tu sistema"}
          </span>
          {proposito && <span style={{ fontSize: 11, lineHeight: 1.4, color: "#5d564d" }}>{proposito}</span>}
        </div>
        {div}
        <div style={cell}>
          <span style={kic}>{filas.find(([l]) => /m[eé]trica|metric/i.test(l))?.[0] ?? (idioma === "en" ? "Metric" : "Métrica")}</span>
          <span style={val}>{metrica}</span>
        </div>
      </div>
      <div style={{ width: 1, height: "clamp(12px,2vh,22px)", background: "linear-gradient(#d8cfc2, #cdbfa9)" }} />
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center", gap: 6,
        textAlign: "center", border: "1px dashed #cdbfa9", borderRadius: 14,
        padding: "12px 18px 14px", maxWidth: 360, background: "rgba(252,250,247,.7)",
      }}>
        <span style={kic}>{filas.find(([l]) => /obst[áa]culo|obstacle/i.test(l))?.[0] ?? (idioma === "en" ? "Obstacle" : "Obstáculo")}</span>
        <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(13px,1.4vw,15px)", lineHeight: 1.3, color: "#6b6459" }}>{obstaculo}</span>
      </div>
    </div>
  );
}

// ─── main export ──────────────────────────────────────────────────────────────

export function SustainView({
  t, idioma, usuarioId, ficha,
}: {
  t: Textos; idioma: "es" | "en"; usuarioId: string; ficha: FichaSnapshot;
}) {
  const datos = (ficha.actual?.datos ?? {}) as { proposito?: string; sistema?: string };
  const proposito = datos.proposito;
  const sistema   = datos.sistema;
  const filasSistema = sistema ? parsearSistema(sistema) : [];

  // Try to recover stored ikigai data from any version in the history
  const ikigai = useMemo(
    () => extractIkigai(ficha.historial, ficha.actual),
    [ficha.historial, ficha.actual],
  );

  // Execution tracking (localStorage, resets each ISO week)
  const [ejecuciones, setEjecuciones] = useState(0);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem(storageKey(usuarioId));
      if (v) setEjecuciones(parseInt(v, 10) || 0);
    } catch { /* SSR / private browsing */ }
  }, [usuarioId]);

  function registrarEjecucion() {
    const next = ejecuciones + 1;
    setEjecuciones(next);
    setFlash(true);
    setTimeout(() => setFlash(false), 1200);
    try { localStorage.setItem(storageKey(usuarioId), String(next)); }
    catch { /* SSR / private browsing */ }
  }

  const cuandoValor = filasSistema.find(([l]) => /cuándo|cuando|when/i.test(l))?.[1] ?? "";
  const frecuencia  = parsearFrecuencia(cuandoValor);
  const nEjecuciones = frecuencia != null ? Math.min(ejecuciones, frecuencia) : ejecuciones;
  const cumplimientoLabel = frecuencia != null
    ? t.sustain_cumplimiento_veces.replace("{n}", String(nEjecuciones)).replace("{total}", String(frecuencia))
    : t.sustain_sin_frecuencia;

  const card: React.CSSProperties = {
    border: `1px solid ${BORDER}`, background: BG_CARD,
    borderRadius: 20, padding: "20px 22px",
    display: "flex", flexDirection: "column", gap: 16,
  };
  const kicker: React.CSSProperties = {
    margin: 0, fontFamily: "var(--font-ibm-plex-mono), monospace",
    fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase" as const, color: "#6b6459",
  };

  return (
    <div style={{ margin: "12px 16px 0", display: "flex", flexDirection: "column", gap: 14 }}>

      {/* ── 1. PURPOSE ───────────────────────────────────────────────────── */}
      {proposito && (
        <div style={card}>
          <h2 style={kicker}>{t.sustain_proposito_kicker}</h2>
          <p style={{
            margin: 0,
            fontFamily: "var(--font-instrument-serif), Georgia, serif",
            fontSize: "clamp(20px,2.6vw,30px)", lineHeight: 1.22, color: "#1b1917",
          }}>
            {proposito}
          </p>
        </div>
      )}

      {/* ── 2. SYSTEM DIAGRAM + EXECUTION BUTTON + RING ──────────────────── */}
      {filasSistema.length > 0 && (
        <div style={{ ...card, gap: 20 }}>
          <h2 style={kicker}>{t.sustain_sistema_kicker}</h2>

          <SistemaFlowDiagram filas={filasSistema} idioma={idioma} proposito={proposito} />

          <div style={{
            borderTop: `1px solid ${BORDER}`, paddingTop: 18,
            display: "flex", alignItems: "center",
            justifyContent: "space-between", flexWrap: "wrap", gap: 16,
          }}>
            <button
              type="button"
              onClick={registrarEjecucion}
              style={{
                border: `1.5px solid ${flash ? "#3a6d63" : "#1b1917"}`,
                background: flash ? "#3a6d63" : "#1b1917",
                color: "#f7f4ef", borderRadius: 999, padding: "13px 26px",
                fontSize: 14, fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
                cursor: "pointer", transition: "background .3s ease, border-color .3s ease",
                display: "flex", alignItems: "center", gap: 8,
              }}
            >
              <span style={{ fontSize: 16, lineHeight: 1 }}>✓</span>
              {flash ? t.sustain_ejecutado_registrado : t.sustain_ejecutado_boton}
            </button>

            {frecuencia != null && (
              <RingChart
                n={nEjecuciones} total={frecuencia}
                label={cumplimientoLabel} sublabel={t.sustain_periodo_semana}
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

      {/* ── 3. IKIGAI ────────────────────────────────────────────────────── */}
      <div style={{ ...card, flexDirection: "row", alignItems: "center", gap: 24, flexWrap: "wrap" }}>
        {/* Real chart if data is available, decorative otherwise */}
        {ikigai
          ? <IkigaiChart ikigai={ikigai} idioma={idioma} />
          : <IkigaiDecorative idioma={idioma} />
        }

        <div style={{ flex: "1 1 180px", display: "flex", flexDirection: "column", gap: 10 }}>
          <h2 style={kicker}>{t.sustain_descubrir_kicker}</h2>

          {/* Show real dimension breakdown if data available */}
          {ikigai && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {DIM_ORDER.map((d) => {
                const dimLabels = idioma === "en" ? DIM_LABELS_EN : DIM_LABELS_ES;
                const cov = Math.min(1, (ikigai.cobertura[d] ?? 0) / 3);
                return (
                  <div key={d} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{
                      width: 6, height: 6, borderRadius: "50%",
                      background: DIM_COLOR[d], flexShrink: 0,
                      opacity: cov > 0 ? 1 : 0.3,
                    }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 4 }}>
                        <span style={{ fontSize: 11.5, color: cov > 0 ? "#3b3630" : "#a8a096" }}>
                          {dimLabels[d]}
                        </span>
                        <span style={{
                          fontFamily: "var(--font-ibm-plex-mono), monospace",
                          fontSize: 9, color: DIM_COLOR[d], opacity: cov > 0 ? 0.9 : 0.4,
                        }}>
                          {ikigai.cobertura[d] ?? 0}
                        </span>
                      </div>
                      {/* progress bar */}
                      <div style={{ height: 2, background: "#ede5d8", borderRadius: 1, marginTop: 2 }}>
                        <div style={{
                          height: "100%", borderRadius: 1,
                          background: DIM_COLOR[d],
                          width: `${cov * 100}%`,
                          opacity: cov > 0 ? 0.7 : 0,
                          transition: "width .6s ease",
                        }} />
                      </div>
                    </div>
                  </div>
                );
              })}
              {ikigai.valores.length > 0 && (
                <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {ikigai.valores.map((v) => (
                    <span key={v} style={{
                      border: "1px solid #c5bcb0", borderRadius: 999,
                      padding: "2px 9px", fontSize: 10.5, color: "#5d564d",
                      fontFamily: "var(--font-ibm-plex-mono), monospace",
                      letterSpacing: ".08em",
                    }}>
                      {v}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {!ikigai && (
            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.6, color: "#5d564d" }}>
              {t.sustain_descubrir_desc}
            </p>
          )}

          {proposito && (
            <p style={{
              margin: 0,
              fontFamily: "var(--font-instrument-serif), Georgia, serif",
              fontSize: "clamp(14px,1.6vw,17px)", lineHeight: 1.3, color: "#1b1917",
              borderLeft: `2px solid ${ACENTO}`, paddingLeft: 12,
            }}>
              {proposito}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
