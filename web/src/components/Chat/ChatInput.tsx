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
    <form
      onSubmit={manejarEnvio}
      style={{
        display: "flex",
        gap: 9,
        alignItems: "center",
        borderTop: "1px solid #e6ddd0",
        padding: "10px 20px 14px",
        background: "rgba(252,250,247,.8)",
      }}
    >
      <input
        type="text"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder={placeholder}
        disabled={deshabilitado}
        style={{
          flex: 1,
          border: "1px solid #e2dbd0",
          borderRadius: 999,
          background: "#fcfaf7",
          padding: "10px 18px",
          fontSize: 14,
          color: "#1b1917",
          outline: "none",
          opacity: deshabilitado ? 0.5 : 1,
          fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        }}
      />
      <button
        type="submit"
        disabled={deshabilitado || !texto.trim()}
        style={{
          border: "none",
          borderRadius: 999,
          background: "#1b1917",
          color: "#f7f4ef",
          width: 36,
          height: 36,
          flexShrink: 0,
          cursor: "pointer",
          fontSize: 14,
          opacity: deshabilitado || !texto.trim() ? 0.4 : 1,
          transition: "opacity .2s ease",
        }}
      >
        →
      </button>
    </form>
  );
}
