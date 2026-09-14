import type { Textos } from "@/lib/i18n";
import { formatear } from "@/lib/formato";
import { parsearSistema } from "@/lib/parseSistema";
import type { Idioma } from "@/lib/types";
import { AccionesCuenta } from "../AccionesCuenta";

// Cabecera de las fases de chat (2, 3 ya refinando, 5) -- reemplaza a
// Sidebar.tsx, que ocupaba toda la altura como una columna fija al
// costado. Pedido explícito del dueño del producto (13/09/2026): "el
// paso entre fases no necesita esa ventana intermedia" -- las fases de
// chat tienen que sentirse la MISMA aplicación que ArbolSelector/
// ValidacionSelector/SistemaSelector, no un panel de resultados aparte.
// Esta cabecera toma el mismo lenguaje visual que esos tres (logo +
// título mono en mayúsculas, misma paleta) en vez de inventar uno
// nuevo, y el detalle "secundario" (fase/racha, resultados completos,
// evolución, exportar, notificaciones -- todo lo que antes vivía
// siempre visible en Sidebar) se movió a PanelDetalles, un panel que se
// abre a pedido con el botón "Detalles" en vez de ocupar espacio todo
// el tiempo.
//
// El propósito, una vez que existe, se muestra siempre acá arriba --
// mismo pedido: "el resto de fases construye un sistema para ese
// propósito, y hace seguimiento a ese sistema para cumplir ese
// propósito", así que tiene sentido que la persona lo tenga siempre a
// la vista, no solo la primera vez que ValidacionSelector/
// SistemaSelector lo muestran. Mismo estilo (caption mono + serif
// grande) que esos dos componentes ya usan para el propósito -- no un
// tratamiento visual nuevo.
export function CabeceraFase({
  idioma,
  onCambiarIdioma,
  t,
  usuarioId,
  requiereLogin,
  proposito,
  sistema,
  onAbrirDetalles,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  t: Textos;
  usuarioId: string | null;
  requiereLogin: boolean;
  proposito: string | null | undefined;
  sistema: string | null | undefined;
  onAbrirDetalles: () => void;
}) {
  const filasSistema = sistema ? parsearSistema(sistema) : [];
  return (
    <header
      style={{
        flex: "none",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        padding: "14px clamp(18px,4vw,46px) 10px",
        background:
          "radial-gradient(70% 60% at 8% 4%, rgba(78,77,134,.10) 0%, rgba(78,77,134,0) 70%), linear-gradient(#fcfaf7 0%, #f5f1ea 100%)",
        borderBottom: "1px solid #e6ddd0",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/telos-brand.png"
            alt="TelOS"
            style={{ width: 30, height: 30, borderRadius: 9, objectFit: "cover", objectPosition: "50% 34%", background: "#1d1b33", flexShrink: 0 }}
          />
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 12.5, letterSpacing: ".32em", textTransform: "uppercase" }}>
            Telos
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "clamp(8px,1.6vw,18px)", flexWrap: "wrap" }}>
          {usuarioId && (
            <span style={{ fontSize: 11.5, color: "#8c8478" }}>{formatear(t.connected_as, { usuario_id: usuarioId })}</span>
          )}

          <button
            onClick={onAbrirDetalles}
            style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "6px 14px", fontSize: 12, cursor: "pointer" }}
          >
            {t.detalles_boton}
          </button>

          <AccionesCuenta idioma={idioma} onCambiarIdioma={onCambiarIdioma} requiereLogin={requiereLogin} logoutLabel={t.logout_button} />
        </div>
      </div>

      {proposito && (
        <div>
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>
            {t.tu_proposito_label}
          </div>
          <p style={{ margin: "2px 0 0", fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(17px,2.1vw,25px)", lineHeight: 1.2, color: "#1b1917" }}>
            {proposito}
          </p>
        </div>
      )}

      {/* "Mi sistema" -- tercer objeto persistente además del propósito
          (ver docstring del módulo): una vez que existe, la persona lo
          tiene siempre a la vista en Construir y Sostener, no solo la
          primera vez que SistemaSelector lo arma. Filas compactas
          (chips), no la lista completa que ya vive en PanelDetalles --
          acá es una referencia rápida, no el detalle. */}
      {filasSistema.length > 0 && (
        <div>
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>
            {t.tu_sistema_label}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {filasSistema.map(([etiqueta, valor], i) => (
              <span
                key={i}
                style={{
                  border: "1px solid #e2dbd0",
                  background: "#fcfaf7",
                  borderRadius: 999,
                  padding: "4px 11px",
                  fontSize: 12,
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
    </header>
  );
}
