import { textoEnriquecido } from "@/lib/textoEnriquecido";
import type { Mensaje } from "@/lib/types";

export function ChatMessage({ mensaje }: { mensaje: Mensaje }) {
  const esUsuario = mensaje.rol === "user";
  return (
    <div className={`flex ${esUsuario ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
          esUsuario ? "bg-primary text-primary-foreground" : "bg-surface text-foreground"
        }`}
      >
        {textoEnriquecido(mensaje.texto)}
      </div>
    </div>
  );
}
