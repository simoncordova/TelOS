"use client";

import { useEffect, useState } from "react";

import { desuscribirPush, enviarPruebaPush, obtenerConfigPush, suscribirPush } from "@/lib/apiCliente";
import { formatear } from "@/lib/formato";
import type { Textos } from "@/lib/i18n";
import { desuscribirseDePush, obtenerSuscripcionActual, pushSoportado, suscribirseAPush } from "@/lib/push";
import type { Idioma } from "@/lib/types";

type Estado = "cargando" | "no-soportado" | "no-configurado" | "inactivo" | "activando" | "activo" | "error";

// Fase 3 del plan de migración: el motivo real de dejar Streamlit, que
// no puede registrar un Service Worker. Opt-in explícito SIEMPRE --
// nunca se pide el permiso de notificaciones solo, sin que la persona
// haya tocado este botón primero (los navegadores penalizan/ignoran
// prompts de permiso no solicitados, y es la práctica correcta de UX).
export function PushOptIn({ idioma, t }: { idioma: Idioma; t: Textos }) {
  const [estado, setEstado] = useState<Estado>("cargando");
  const [clavePublica, setClavePublica] = useState("");
  const [resultadoPrueba, setResultadoPrueba] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      if (!pushSoportado()) {
        if (!cancelado) setEstado("no-soportado");
        return;
      }
      const config = await obtenerConfigPush();
      if (cancelado) return;
      if (!config.configurado) {
        setEstado("no-configurado");
        return;
      }
      setClavePublica(config.clavePublica);
      const suscripcionActual = await obtenerSuscripcionActual();
      if (!cancelado) setEstado(suscripcionActual ? "activo" : "inactivo");
    })();
    return () => {
      cancelado = true;
    };
  }, []);

  async function activar() {
    setEstado("activando");
    try {
      const suscripcion = await suscribirseAPush(clavePublica);
      await suscribirPush(suscripcion);
      setEstado("activo");
    } catch (e) {
      console.error("No se pudo activar push:", e);
      setEstado("error");
    }
  }

  async function desactivar() {
    const endpoint = await desuscribirseDePush();
    if (endpoint) await desuscribirPush(endpoint).catch(() => undefined);
    setEstado("inactivo");
    setResultadoPrueba(null);
  }

  async function probar() {
    const resultado = await enviarPruebaPush(idioma);
    setResultadoPrueba(formatear(t.push_prueba_resultado, { enviados: resultado.enviados }));
  }

  // Nada que mostrar todavía, o esta build no tiene VAPID configurado
  // (deploy sin Fase 3 activada) -- no soportado tampoco se muestra, no
  // vale la pena avisarle a cada persona en un navegador viejo.
  if (estado === "cargando" || estado === "no-configurado" || estado === "no-soportado") return null;

  return (
    <div className="rounded-xl bg-surface p-3 text-sm">
      <p className="mb-2 font-medium">{t.push_titulo}</p>
      {estado === "inactivo" && (
        <button onClick={activar} className="rounded-full bg-primary px-3 py-1.5 text-xs text-primary-foreground">
          {t.push_activar}
        </button>
      )}
      {estado === "activando" && <p className="text-foreground/60">{t.push_activando}</p>}
      {estado === "error" && (
        <div className="flex flex-col gap-2">
          <p className="text-foreground/60">{t.push_error}</p>
          <button onClick={activar} className="self-start rounded-full bg-primary px-3 py-1.5 text-xs text-primary-foreground">
            {t.push_activar}
          </button>
        </div>
      )}
      {estado === "activo" && (
        <div className="flex flex-col gap-2">
          <p className="text-foreground/60">{t.push_activado}</p>
          <div className="flex gap-2">
            <button onClick={probar} className="rounded-full bg-primary px-3 py-1.5 text-xs text-primary-foreground">
              {t.push_probar}
            </button>
            <button onClick={desactivar} className="rounded-full bg-background px-3 py-1.5 text-xs">
              {t.push_desactivar}
            </button>
          </div>
          {resultadoPrueba && <p className="text-xs text-foreground/60">{resultadoPrueba}</p>}
        </div>
      )}
    </div>
  );
}
