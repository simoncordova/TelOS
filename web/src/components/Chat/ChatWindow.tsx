"use client";

import { useEffect, useRef } from "react";

import type { Mensaje } from "@/lib/types";
import { ChatMessage } from "./ChatMessage";

export function ChatWindow({ mensajes, cargando }: { mensajes: Mensaje[]; cargando: boolean }) {
  const finRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [mensajes.length, cargando]);

  return (
    <div
      style={{
        display: "flex",
        flex: 1,
        flexDirection: "column",
        gap: 12,
        overflowY: "auto",
        minHeight: 0,
        padding: "16px 20px",
      }}
    >
      {mensajes.map((mensaje, i) => (
        <ChatMessage key={i} mensaje={mensaje} />
      ))}
      {cargando && (
        <div style={{ display: "flex", justifyContent: "flex-start" }}>
          <div
            style={{
              borderRadius: 18,
              padding: "10px 16px",
              fontSize: 14,
              background: "#f0ece4",
              color: "#6b6459",
              border: "1px solid #e2dbd0",
              fontFamily: "var(--font-ibm-plex-mono), monospace",
              letterSpacing: "0.08em",
            }}
          >
            …
          </div>
        </div>
      )}
      <div ref={finRef} />
    </div>
  );
}
