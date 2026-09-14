import type { Textos } from "@/lib/i18n";
import { formatear } from "@/lib/formato";
import { urlLogout } from "@/lib/apiCliente";
import type { FichaSnapshot, Idioma } from "@/lib/types";
import { PushOptIn } from "../Notifications/PushOptIn";
import { EvolucionHistorial } from "./EvolucionHistorial";
import { ExportarButton } from "./ExportarButton";
import { FaseActual } from "./FaseActual";
import { ResultadosPanel } from "./ResultadosPanel";

// Port de la barra lateral de ui/app.py: idioma, sesión, "Fase actual" +
// "🔥 Racha", "Tus resultados", "Tu evolución", exportar.
// Estilo actualizado al sistema visual warm de la maqueta (sin navy).
export function Sidebar({
  idioma,
  onCambiarIdioma,
  t,
  usuarioId,
  requiereLogin,
  fase,
  ficha,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  t: Textos;
  usuarioId: string | null;
  requiereLogin: boolean;
  fase: number;
  ficha: FichaSnapshot | null;
}) {
  const datos = (ficha?.actual?.datos ?? {}) as { proposito?: string; sistema?: string };

  return (
    <aside
      style={{
        display: "flex",
        width: "100%",
        flexDirection: "column",
        gap: 16,
        overflowY: "auto",
        borderBottom: "1px solid #e6ddd0",
        padding: 20,
        background: "#f5f1ea",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
      }}
      className="md:h-full md:w-72 md:border-r md:border-b-0"
    >
      {/* Logo + título */}
      <div>
        <h1
          style={{
            margin: 0,
            fontFamily: "var(--font-ibm-plex-mono), monospace",
            fontSize: 13,
            letterSpacing: ".34em",
            textTransform: "uppercase",
            color: "#a4552f",
          }}
        >
          Telos
        </h1>
        <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6b6459" }}>{t.caption}</p>
      </div>

      {/* Selector de idioma */}
      <div style={{ display: "flex", gap: 6 }}>
        {(["en", "es"] as const).map((opcion) => {
          const activo = idioma === opcion;
          return (
            <button
              key={opcion}
              onClick={() => onCambiarIdioma(opcion)}
              style={{
                border: `1px solid ${activo ? "#a4552f" : "#e2dbd0"}`,
                background: activo ? "rgba(164,85,47,.08)" : "transparent",
                color: activo ? "#a4552f" : "#5d564d",
                borderRadius: 999,
                padding: "5px 14px",
                fontSize: 12,
                cursor: "pointer",
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                letterSpacing: ".1em",
                textTransform: "uppercase",
                transition: "all .25s ease",
              }}
            >
              {opcion === "es" ? "Español" : "English"}
            </button>
          );
        })}
      </div>

      {/* Usuario */}
      {usuarioId && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
          <span style={{ color: "#6b6459" }}>{formatear(t.connected_as, { usuario_id: usuarioId })}</span>
          {requiereLogin && (
            <a href={urlLogout()} style={{ color: "#a4552f", textDecoration: "underline", fontSize: 12 }}>
              {t.logout_button}
            </a>
          )}
        </div>
      )}

      <FaseActual idioma={idioma} t={t} fase={fase} racha={ficha?.racha ?? 0} />

      <hr style={{ border: "none", borderTop: "1px solid #e2dbd0", margin: 0 }} />

      <ResultadosPanel t={t} proposito={datos.proposito} sistema={datos.sistema} />

      <hr style={{ border: "none", borderTop: "1px solid #e2dbd0", margin: 0 }} />

      {ficha && <EvolucionHistorial idioma={idioma} t={t} ficha={ficha} />}

      <ExportarButton idioma={idioma} t={t} tieneProposito={Boolean(datos.proposito)} />

      <PushOptIn idioma={idioma} t={t} />
    </aside>
  );
}
