import type { Textos } from "@/lib/i18n";

// Red de seguridad, no un flujo esperado: se muestra únicamente cuando
// `faseActual` no calza con ninguna de las fases válidas (0-5) que
// TelosApp.tsx sabe renderizar -- ver determinarVista() ahí. Antes, ese
// caso caía en silencio al `else` genérico (chat + sidebar con
// "Propósito"/"Sistema" vacíos, racha "—"), un dashboard que se veía
// legítimo pero no lo era -- reportado como bug real (13/09/2026): un
// valor de fase inesperado quedaba indistinguible de "todavía no
// definiste nada". Esta pantalla reemplaza ese fallback silencioso por
// un error explícito, para que nunca se confunda con un estado vacío
// normal de la app.
export function EstadoError({ t }: { t: Textos }) {
  return (
    <main className="flex min-h-0 flex-1 items-center justify-center overflow-y-auto" style={{ background: "#f5f1ea" }}>
      <div
        style={{
          margin: 20,
          maxWidth: 420,
          borderRadius: 18,
          border: "1px solid #e2c7b8",
          background: "#fcfaf7",
          padding: "24px 26px",
          textAlign: "center",
        }}
      >
        <p
          style={{
            margin: "0 0 10px",
            fontFamily: "var(--font-ibm-plex-mono), monospace",
            fontSize: 12,
            letterSpacing: ".2em",
            textTransform: "uppercase",
            color: "#a4552f",
          }}
        >
          {t.error_estado_titulo}
        </p>
        <p
          style={{
            margin: "0 0 20px",
            fontSize: 14,
            lineHeight: 1.6,
            color: "#5d564d",
            fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
          }}
        >
          {t.error_estado_texto}
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            border: "none",
            borderRadius: 999,
            background: "#a4552f",
            color: "#fcfaf7",
            padding: "9px 22px",
            fontSize: 13,
            cursor: "pointer",
            fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
          }}
        >
          {t.error_estado_boton}
        </button>
      </div>
    </main>
  );
}
