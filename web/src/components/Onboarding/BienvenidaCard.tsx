import type { Textos } from "@/lib/i18n";
import { textoEnriquecido } from "@/lib/textoEnriquecido";

// Port de la pantalla de bienvenida en ui/app.py: solo para quien
// todavía no tiene nombre guardado (Paso 0).
export function BienvenidaCard({ t }: { t: Textos }) {
  return (
    <div
      style={{
        margin: "16px 20px 0",
        borderRadius: 18,
        border: "1px solid #e2dbd0",
        background: "#fcfaf7",
        padding: "18px 20px",
      }}
    >
      <h2
        style={{
          margin: "0 0 8px",
          fontFamily: "var(--font-instrument-serif), Georgia, serif",
          fontWeight: 400,
          fontSize: 22,
          lineHeight: 1.2,
          color: "#1b1917",
        }}
      >
        {t.bienvenida_titulo}
      </h2>
      <p
        style={{
          margin: 0,
          fontSize: 14,
          lineHeight: 1.6,
          color: "#5d564d",
          whiteSpace: "pre-wrap",
          fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        }}
      >
        {textoEnriquecido(t.bienvenida_texto)}
      </p>
    </div>
  );
}
