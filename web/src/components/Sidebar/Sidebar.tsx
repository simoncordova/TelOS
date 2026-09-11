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
// "🔥 Racha", "Tus resultados", "Tu evolución", exportar. Se relee la
// ficha en cada respuesta del backend (ver TelosApp), así que todo esto
// se actualiza solo apenas un agente guarda una versión nueva -- mismo
// comportamiento que el rerun automático de Streamlit.
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
    <aside className="flex w-full flex-col gap-4 border-b border-surface p-4 md:w-72 md:border-r md:border-b-0 md:h-screen md:overflow-y-auto">
      <div>
        <h1 className="text-lg font-semibold text-primary">Telos</h1>
        <p className="text-xs text-foreground/60">{t.caption}</p>
      </div>

      <div className="flex gap-2 text-xs">
        {(["es", "en"] as const).map((opcion) => (
          <button
            key={opcion}
            onClick={() => onCambiarIdioma(opcion)}
            className={`rounded-full px-3 py-1 ${idioma === opcion ? "bg-primary text-primary-foreground" : "bg-surface"}`}
          >
            {opcion === "es" ? "Español" : "English"}
          </button>
        ))}
      </div>

      {usuarioId && (
        <div className="flex items-center justify-between text-xs">
          <span className="text-foreground/60">{formatear(t.connected_as, { usuario_id: usuarioId })}</span>
          {requiereLogin && (
            <a href={urlLogout()} className="underline">
              {t.logout_button}
            </a>
          )}
        </div>
      )}

      <FaseActual idioma={idioma} t={t} fase={fase} racha={ficha?.racha ?? 0} />

      <hr className="border-surface" />

      <ResultadosPanel t={t} proposito={datos.proposito} sistema={datos.sistema} />

      <hr className="border-surface" />

      {ficha && <EvolucionHistorial idioma={idioma} t={t} ficha={ficha} />}

      <ExportarButton idioma={idioma} t={t} tieneProposito={Boolean(datos.proposito)} />

      <PushOptIn idioma={idioma} t={t} />
    </aside>
  );
}
