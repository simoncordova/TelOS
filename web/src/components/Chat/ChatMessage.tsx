import { textoEnriquecido } from "@/lib/textoEnriquecido";
import type { Mensaje } from "@/lib/types";

export function ChatMessage({ mensaje }: { mensaje: Mensaje }) {
  const esUsuario = mensaje.rol === "user";
  return (
    <div style={{ display: "flex", justifyContent: esUsuario ? "flex-end" : "flex-start" }}>
      <div
        style={{
          maxWidth: "85%",
          borderRadius: 18,
          padding: "10px 16px",
          fontSize: 14,
          lineHeight: 1.55,
          whiteSpace: "pre-wrap",
          background: esUsuario ? "#1b1917" : "#f0ece4",
          color: esUsuario ? "#f7f4ef" : "#1b1917",
          border: `1px solid ${esUsuario ? "#1b1917" : "#e2dbd0"}`,
          fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        }}
      >
        {textoEnriquecido(mensaje.texto)}
      </div>
    </div>
  );
}
