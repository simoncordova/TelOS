"use client";

import { useState } from "react";
import type { FormEvent } from "react";

export function ChatInput({
  placeholder,
  deshabilitado,
  onEnviar,
}: {
  placeholder: string;
  deshabilitado: boolean;
  onEnviar: (texto: string) => void;
}) {
  const [texto, setTexto] = useState("");

  function manejarEnvio(e: FormEvent) {
    e.preventDefault();
    const limpio = texto.trim();
    if (!limpio || deshabilitado) return;
    onEnviar(limpio);
    setTexto("");
  }

  return (
    <form onSubmit={manejarEnvio} className="flex gap-2 border-t border-surface p-3">
      <input
        type="text"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder={placeholder}
        disabled={deshabilitado}
        className="flex-1 rounded-full bg-surface px-4 py-2 text-sm outline-none disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={deshabilitado || !texto.trim()}
        className="rounded-full bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
      >
        ➤
      </button>
    </form>
  );
}
