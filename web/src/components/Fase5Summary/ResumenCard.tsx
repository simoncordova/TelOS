import type { Textos } from "@/lib/i18n";
import { textoEnriquecido } from "@/lib/textoEnriquecido";

// Port de la tarjeta de Vista de resumen (Fase 5) en ui/app.py: el texto
// viene entero de agents.seguimiento.construir_vista_resumen (código, no
// el modelo) -- este componente solo lo muestra, no lo recalcula.
export function ResumenCard({ t, vistaResumen }: { t: Textos; vistaResumen: string }) {
  return (
    <div className="mx-4 mt-3 rounded-2xl border border-primary/30 bg-surface p-4">
      <h2 className="mb-2 text-sm font-semibold">{t.resumen_titulo}</h2>
      <p className="text-sm leading-relaxed whitespace-pre-wrap">{textoEnriquecido(vistaResumen)}</p>
    </div>
  );
}
