import type { Textos } from "@/lib/i18n";
import { NOMBRES_FASE } from "@/lib/i18n";
import type { Idioma } from "@/lib/types";

// Port de las dos st.metric de ui/app.py (Fase actual + 🔥 Racha) --
// la racha es del sistema/hábito (constancia), no del propósito, que
// sigue sin ser una "meta" que se completa (spec sección 8).
export function FaseActual({
  idioma,
  t,
  fase,
  racha,
}: {
  idioma: Idioma;
  t: Textos;
  fase: number;
  racha: number;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="rounded-xl bg-surface p-3">
        <p className="text-xs text-foreground/60">{t.fase_label}</p>
        <p className="text-sm font-semibold">{NOMBRES_FASE[idioma][fase] ?? fase}</p>
      </div>
      <div className="rounded-xl bg-surface p-3">
        <p className="text-xs text-foreground/60">{t.racha_label}</p>
        <p className="text-sm font-semibold">{racha > 0 ? racha : "—"}</p>
      </div>
    </div>
  );
}
