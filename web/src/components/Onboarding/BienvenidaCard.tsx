import type { Textos } from "@/lib/i18n";
import { textoEnriquecido } from "@/lib/textoEnriquecido";

// Port de la pantalla de bienvenida en ui/app.py: solo para quien
// todavía no tiene nombre guardado (Paso 0). Breve a propósito -- no un
// wizard de onboarding, mismo tono que le pide el spec al Explorador
// ("ágil y alcanzable, no como el inicio de un proceso largo").
export function BienvenidaCard({ t }: { t: Textos }) {
  return (
    <div className="mx-4 mt-3 rounded-2xl border border-surface p-4">
      <h2 className="mb-2 text-base font-semibold">{t.bienvenida_titulo}</h2>
      <p className="text-sm leading-relaxed whitespace-pre-wrap">{textoEnriquecido(t.bienvenida_texto)}</p>
    </div>
  );
}
