import type { Textos } from "@/lib/i18n";
import type { FichaSnapshot, Idioma } from "@/lib/types";
import { PushOptIn } from "../Notifications/PushOptIn";
import { EvolucionHistorial } from "../Sidebar/EvolucionHistorial";
import { ExportarButton } from "../Sidebar/ExportarButton";
import { FaseActual } from "../Sidebar/FaseActual";
import { ResultadosPanel } from "../Sidebar/ResultadosPanel";

// Todo lo que antes vivía siempre visible en Sidebar.tsx (fase/racha,
// resultados, evolución, exportar, notificaciones) -- ahora a pedido,
// como panel superpuesto que abre el botón "Detalles" de CabeceraFase,
// en vez de una columna fija que le resta espacio al chat todo el
// tiempo. Mismos componentes de Sidebar/, sin cambios de lógica -- solo
// cambia el contenedor que los envuelve.
export function PanelDetalles({
  idioma,
  t,
  fase,
  ficha,
  onCerrar,
}: {
  idioma: Idioma;
  t: Textos;
  fase: number;
  ficha: FichaSnapshot | null;
  onCerrar: () => void;
}) {
  const datos = (ficha?.actual?.datos ?? {}) as { proposito?: string; sistema?: string };

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(28,25,22,.3)", backdropFilter: "blur(3px)", display: "flex", justifyContent: "flex-end", zIndex: 70 }}
      onClick={onCerrar}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(360px, 92vw)",
          height: "100%",
          overflowY: "auto",
          background: "#f5f1ea",
          borderLeft: "1px solid #e2dbd0",
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
          color: "#1b1917",
          animation: "telos-panel-rise .25s ease both",
        }}
      >
        <style>{`@keyframes telos-panel-rise { from { opacity:0; transform:translateX(12px); } to { opacity:1; transform:none; } }`}</style>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 11, letterSpacing: ".16em", textTransform: "uppercase", color: "#6b6459" }}>
            {t.detalles_boton}
          </span>
          <button
            onClick={onCerrar}
            style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "4px 14px", fontSize: 12, cursor: "pointer" }}
          >
            {t.cerrar_boton}
          </button>
        </div>

        <FaseActual idioma={idioma} t={t} fase={fase} racha={ficha?.racha ?? 0} />

        <hr style={{ border: "none", borderTop: "1px solid #e2dbd0", margin: 0 }} />

        <ResultadosPanel t={t} proposito={datos.proposito} sistema={datos.sistema} />

        <hr style={{ border: "none", borderTop: "1px solid #e2dbd0", margin: 0 }} />

        {ficha && <EvolucionHistorial idioma={idioma} t={t} ficha={ficha} />}

        <ExportarButton idioma={idioma} t={t} tieneProposito={Boolean(datos.proposito)} />

        <PushOptIn idioma={idioma} t={t} />
      </div>
    </div>
  );
}
