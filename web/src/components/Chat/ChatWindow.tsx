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
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
      {mensajes.map((mensaje, i) => (
        <ChatMessage key={i} mensaje={mensaje} />
      ))}
      {cargando && (
        <div className="flex justify-start">
          <div className="rounded-2xl bg-surface px-4 py-2 text-sm text-foreground/60">...</div>
        </div>
      )}
      <div ref={finRef} />
    </div>
  );
}
