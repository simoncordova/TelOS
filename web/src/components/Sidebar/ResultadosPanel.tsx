import type { Textos } from "@/lib/i18n";
import { parsearSistema } from "@/lib/parseSistema";

// Port de "Tus resultados" en ui/app.py -- propósito como texto plano,
// sistema como checklist si el modelo siguió el formato de líneas
// etiquetadas (_parsear_sistema), texto plano si no.
export function ResultadosPanel({
  t,
  proposito,
  sistema,
}: {
  t: Textos;
  proposito: string | null | undefined;
  sistema: string | null | undefined;
}) {
  const filasSistema = sistema ? parsearSistema(sistema) : [];

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold">{t.panel_titulo}</h2>

      <div>
        <p className="mb-1 text-xs font-medium text-foreground/70">{t.panel_proposito}</p>
        <p className="rounded-lg bg-surface p-2 text-sm whitespace-pre-wrap">{proposito || t.panel_vacio_proposito}</p>
      </div>

      <div>
        <p className="mb-1 text-xs font-medium text-foreground/70">{t.panel_sistema}</p>
        {filasSistema.length > 1 ? (
          <ul className="flex flex-col gap-1 rounded-lg bg-surface p-2 text-sm">
            {filasSistema.map(([etiqueta, valor], i) => (
              <li key={i}>
                ✅ {etiqueta ? <strong>{etiqueta}:</strong> : null} {valor}
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-lg bg-surface p-2 text-sm whitespace-pre-wrap">{sistema || t.panel_vacio_sistema}</p>
        )}
      </div>
    </div>
  );
}
