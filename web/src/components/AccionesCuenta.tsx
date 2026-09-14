import type { Idioma } from "@/lib/types";
import { urlLogout } from "@/lib/apiCliente";

// Compartido por CabeceraFase.tsx (fases de chat) Y por los tres
// selectores visuales (ArbolSelector/ValidacionSelector/SistemaSelector)
// -- bug real reportado (14/09/2026): cambiar de idioma y cerrar sesión
// solo existían en la cabecera de las fases de chat, así que alguien
// que pasaba todo el tiempo en Fase 1, 3 (antes del refinado) o 4 nunca
// tenía forma de hacer ninguna de las dos cosas. Un solo componente
// chico en vez de repetir el markup en cada uno de los 4 lugares --
// misma idea que agents/_modelo.py centralizando reglas compartidas
// entre los 5 prompts, ahora del lado del frontend.
//
// `logoutLabel` (no `t: Textos`) a propósito: los tres selectores
// tienen su PROPIO diccionario de textos local (no el `Textos` de
// web/src/lib/i18n.ts), así que este componente no depende de ningún
// tipo de textos en particular -- cada caller le pasa el string ya
// traducido que corresponda.
export function AccionesCuenta({
  idioma,
  onCambiarIdioma,
  requiereLogin,
  logoutLabel,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  requiereLogin: boolean;
  logoutLabel: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
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
                padding: "4px 12px",
                fontSize: 11,
                cursor: "pointer",
                fontFamily: "var(--font-ibm-plex-mono), monospace",
                letterSpacing: ".08em",
                textTransform: "uppercase",
              }}
            >
              {opcion === "es" ? "Español" : "English"}
            </button>
          );
        })}
      </div>

      {requiereLogin && (
        <a href={urlLogout()} style={{ color: "#a4552f", textDecoration: "underline", fontSize: 11.5, whiteSpace: "nowrap" }}>
          {logoutLabel}
        </a>
      )}
    </div>
  );
}
