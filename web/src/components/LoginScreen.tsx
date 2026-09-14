import type { Idioma } from "@/lib/types";

// Pantalla de inicio pre-auth: replica la pantalla de bienvenida de
// ArbolSelector (maqueta/TELOS.dc.html, estado "welcome") como Server
// Component estático. El gráfico SVG Ikigai vacío + "Comenzar exploración"
// lanzan /api/auth/login al hacer clic -- mismo flujo que antes pero
// envuelto en el diseño visual de la maqueta en lugar de la pantalla
// de login básica anterior.
export function LoginScreen({ idioma }: { idioma: Idioma }) {
  const es = idioma === "es";

  return (
    <div
      style={{
        height: "100vh",
        minHeight: 520,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        background:
          "radial-gradient(80% 55% at 50% 62%, rgba(226,164,74,.20) 0%, rgba(226,164,74,0) 62%), radial-gradient(70% 60% at 8% 4%, rgba(78,77,134,.16) 0%, rgba(78,77,134,0) 70%), radial-gradient(70% 60% at 95% 6%, rgba(58,109,99,.12) 0%, rgba(58,109,99,0) 70%), linear-gradient(#fcfaf7 0%, #f5f1ea 60%, #efe8dd 100%)",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
      }}
    >
      <style>{`
        @keyframes telos-breathe { 0%,100% { opacity:.55; transform:scale(1); } 50% { opacity:.85; transform:scale(1.035); } }
        @keyframes telos-rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
        .telos-login-start { animation: telos-rise .8s ease both; }
      `}</style>

      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 20,
          padding: "12px clamp(18px,4vw,46px) 6px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/telos-brand.png"
            alt="TelOS"
            style={{ width: 34, height: 34, borderRadius: 11, objectFit: "cover", objectPosition: "50% 34%", background: "#1d1b33", flexShrink: 0 }}
          />
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 13, letterSpacing: ".34em", textTransform: "uppercase" }}>
              Telos
            </span>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".14em", textTransform: "uppercase", color: "#9c948a" }}>
              {es ? "Exploración del propósito" : "Purpose exploration"}
            </span>
          </div>
        </div>

        {/* Selector de idioma en header */}
        <div style={{ display: "flex", gap: "clamp(10px,2vw,26px)", flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 6 }}>
            {(["en", "es"] as const).map((op) => (
              <a
                key={op}
                href={`?idioma=${op}`}
                style={{
                  border: `1px solid ${idioma === op ? "#a4552f" : "#e2dbd0"}`,
                  background: idioma === op ? "rgba(164,85,47,.08)" : "transparent",
                  color: idioma === op ? "#a4552f" : "#5d564d",
                  borderRadius: 999,
                  padding: "5px 14px",
                  fontSize: 11,
                  fontFamily: "var(--font-ibm-plex-mono), monospace",
                  letterSpacing: ".12em",
                  textTransform: "uppercase",
                  textDecoration: "none",
                  transition: "all .25s ease",
                }}
              >
                {op === "es" ? "Español" : "English"}
              </a>
            ))}
          </div>
        </div>
      </header>

      {/* Gráfico Ikigai central */}
      <main
        style={{
          flex: "1 1 auto",
          minHeight: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          padding: "4px 12px",
        }}
      >
        <div
          style={{
            position: "relative",
            height: "min(100%, 58vw, 560px)",
            aspectRatio: "1/1",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* SVG Ikigai vacío */}
          <svg
            viewBox="-270 -270 540 540"
            width="100%"
            height="100%"
            preserveAspectRatio="xMidYMid meet"
            style={{ position: "absolute", inset: 0, overflow: "visible" }}
          >
            {/* Círculos de fondo */}
            {[230, 176, 120, 66].map((r, i) => (
              <circle key={i} r={r} fill="none" stroke="#1b1917" strokeWidth={0.5} opacity={0.09} />
            ))}
            {/* 4 sectores de dimensión vacíos */}
            {[
              { a: -135, c: "#c8801f", label: es ? "AMAS" : "LOVE" },
              { a: -45,  c: "#4e4d86", label: es ? "DESTACAS" : "GREAT AT" },
              { a: 45,   c: "#a8532c", label: es ? "APORTA VALOR" : "PAID FOR" },
              { a: 135,  c: "#3a6d63", label: es ? "EL MUNDO NECESITA" : "WORLD NEEDS" },
            ].map((d, i) => {
              const cx = Math.cos((d.a * Math.PI) / 180) * 150;
              const cy = Math.sin((d.a * Math.PI) / 180) * 150;
              const lx = Math.cos((d.a * Math.PI) / 180) * 252;
              const ly = Math.sin((d.a * Math.PI) / 180) * 252;
              return (
                <g key={i}>
                  <circle cx={cx} cy={cy} r={66} fill={d.c} opacity={0.05} />
                  <circle cx={cx} cy={cy} r={3.4} fill="#c3bab0" opacity={0.6} />
                  <text
                    x={lx}
                    y={ly + (ly < -40 ? -8 : ly > 40 ? 16 : 4)}
                    textAnchor="middle"
                    fill="#a8a096"
                    fontSize={11.5}
                    fontFamily="var(--font-ibm-plex-mono), monospace"
                    letterSpacing={1.6}
                  >
                    {d.label}
                  </text>
                </g>
              );
            })}
            {/* Centro vacío pulsante */}
            <circle r={52} fill="#a4552f" opacity={0.02} />
            <circle
              r={26}
              fill="none"
              stroke="#a4552f"
              strokeWidth={0.7}
              opacity={0.18}
              strokeDasharray="18 8"
              style={{ animation: "telos-breathe 6s ease-in-out infinite" }}
            />
          </svg>

          {/* Texto central */}
          <div
            style={{
              position: "absolute",
              left: "24%",
              top: "29%",
              width: "52%",
              height: "42%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              gap: 6,
              pointerEvents: "none",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-instrument-serif), Georgia, serif",
                fontSize: "clamp(16px,2vw,27px)",
                lineHeight: 1.1,
                color: "#1b1917",
              }}
            >
              {es ? "Descubramos qué te mueve." : "Let's find what moves you."}
            </div>
            <div style={{ fontSize: 11.5, lineHeight: 1.35, color: "#6b6459" }}>
              {es ? "No hay respuestas correctas." : "There are no right answers."}
            </div>
          </div>
        </div>
      </main>

      {/* Sección inferior: banner imagen + botones */}
      <section
        className="telos-login-start"
        style={{
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 13,
          padding: "0 24px clamp(14px,2.5vh,40px)",
        }}
      >
        {/* Banner imagen */}
        <div
          style={{
            width: "100%",
            maxWidth: 1040,
            height: "clamp(54px,7vh,104px)",
            borderRadius: 18,
            overflow: "hidden",
            position: "relative",
            border: "1px solid #e2dbd0",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/telos-brand.png"
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 86%", display: "block" }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "linear-gradient(to top, rgba(244,241,236,.55) 0%, rgba(244,241,236,0) 55%)",
            }}
          />
        </div>

        {/* Botones */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
          <a
            href={`/api/auth/login?idioma=${idioma}`}
            style={{
              border: "1px solid #1b1917",
              background: "#1b1917",
              color: "#f7f4ef",
              borderRadius: 999,
              padding: "14px 30px",
              fontSize: 14.5,
              letterSpacing: ".02em",
              textDecoration: "none",
              cursor: "pointer",
              transition: "background .3s ease",
            }}
          >
            {es ? "Comenzar exploración" : "Start exploring"}
          </a>
        </div>

        <div
          style={{
            fontFamily: "var(--font-ibm-plex-mono), monospace",
            fontSize: 10,
            letterSpacing: ".14em",
            textTransform: "uppercase",
            color: "#a8a096",
          }}
        >
          {es ? "Sin preguntas. Solo elecciones." : "No questions. Just choices."}
        </div>
      </section>
    </div>
  );
}
