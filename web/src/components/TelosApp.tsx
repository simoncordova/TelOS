"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { abrirSesion, enviarMensaje } from "@/lib/apiCliente";
import { TEXTOS } from "@/lib/i18n";
import { leerEventosSSE } from "@/lib/sse";
import type { FichaSnapshot, Idioma, Mensaje } from "@/lib/types";
import { ChatInput } from "./Chat/ChatInput";
import { ChatWindow } from "./Chat/ChatWindow";
import { OpcionesForm } from "./Chat/OpcionesForm";
import { ResumenCard } from "./Fase5Summary/ResumenCard";
import { JourneyMap } from "./JourneyMap/JourneyMap";
import type { Festejo } from "./Notifications/Celebracion";
import { Celebracion } from "./Notifications/Celebracion";
import { BienvenidaCard } from "./Onboarding/BienvenidaCard";
import { Sidebar } from "./Sidebar/Sidebar";

// Dueño solo del idioma elegido -- todo lo demás (mensajes, ficha,
// festejos) vive en <Conversacion>, remontada con key={idioma}. Cambiar
// de idioma arranca una sesión nueva del lado del backend igual que en
// ui/app.py (clave_sesion = (usuario_id, idioma)); acá el remount por
// key logra el mismo reinicio de estado sin tener que resetear cada
// pieza a mano dentro de un efecto.
export function TelosApp({
  usuarioId,
  requiereLogin,
  idiomaInicial,
}: {
  usuarioId: string;
  requiereLogin: boolean;
  idiomaInicial: Idioma;
}) {
  const [idioma, setIdioma] = useState<Idioma>(idiomaInicial);
  return (
    <Conversacion key={idioma} idioma={idioma} onCambiarIdioma={setIdioma} usuarioId={usuarioId} requiereLogin={requiereLogin} />
  );
}

// Port 1:1 del script principal de ui/app.py -- misma secuencia
// (abrir_conversacion al montar, _procesar_turno por cada
// mensaje/opción, festejos según el mismo criterio de
// fase_antes/fase_actual) sobre las mismas rutas HTTP que expone api/.
//
// Limitación conocida (MVP, no la resuelve Streamlit tampoco): un
// refresh de página reinicia el historial visible del chat -- Streamlit
// hace exactamente lo mismo en una sesión nueva (st.session_state
// vuelve a [] y abrir_conversacion() se llama de nuevo). El progreso
// real (ficha, turnos guardados) nunca se pierde en ninguno de los dos
// casos, solo la vista de mensajes de esta sesión de navegador.
function Conversacion({
  idioma,
  onCambiarIdioma,
  usuarioId,
  requiereLogin,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  usuarioId: string;
  requiereLogin: boolean;
}) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [opcionesPendientes, setOpcionesPendientes] = useState<string[]>([]);
  const [faseActual, setFaseActual] = useState(1);
  const [ficha, setFicha] = useState<FichaSnapshot | null>(null);
  // Arranca en true a propósito (no vía setState en el efecto de abajo):
  // este componente se remonta entero cada vez que cambia el idioma
  // (key={idioma} en TelosApp), así que "recién montado" y "cargando la
  // apertura de sesión" son lo mismo.
  const [cargando, setCargando] = useState(true);
  const [festejo, setFestejo] = useState<Festejo | null>(null);

  const t = TEXTOS[idioma];

  // Refs, no dependencias directas del useCallback de abajo: dentro de
  // procesarTurno necesitamos el valor de ficha/faseActual vigente AL
  // MOMENTO DE LLAMAR la función, no el que tenía cuando React la creó
  // por última vez (closure stale) -- mismo problema que Python no tiene
  // acá porque ui/app.py lee `sesion.fase_actual` como atributo mutable
  // de un objeto, no como estado de React. Sincronizados en un efecto
  // (no durante el render) para no mutar un ref fuera de ese punto.
  const fichaRef = useRef(ficha);
  const faseActualRef = useRef(faseActual);
  useEffect(() => {
    fichaRef.current = ficha;
    faseActualRef.current = faseActual;
  }, [ficha, faseActual]);

  // El agente habla primero siempre, nueva conversación o retomada
  // (Fase 5 muestra su resumen apenas abre, no después) -- corre una
  // sola vez por montaje: el cambio de idioma ya remonta este
  // componente entero (ver TelosApp), así que no hace falta reaccionar
  // a `idioma` acá también.
  useEffect(() => {
    let cancelado = false;

    (async () => {
      const respuesta = await abrirSesion(idioma);
      for await (const { evento, datos } of leerEventosSSE(respuesta)) {
        if (cancelado) return;
        if (evento === "mensaje") {
          const d = datos as { fase: number; texto: string; opciones: string[] };
          setMensajes((prev) => [...prev, { rol: "assistant", texto: d.texto }]);
          setFaseActual(d.fase);
          setOpcionesPendientes(d.opciones);
        } else if (evento === "ficha") {
          setFicha(datos as FichaSnapshot);
        } else if (evento === "error") {
          // El backend no pudo completar el turno (ej. Bedrock no
          // disponible) -- api/sse.py ya cortó el resto del generador,
          // así que acá solo queda avisar en vez de dejar a la persona
          // mirando un chat que nunca contesta.
          console.error("Error del backend:", (datos as { detalle: string }).detalle);
          setMensajes((prev) => [...prev, { rol: "assistant", texto: t.error_generico }]);
        }
      }
      if (!cancelado) setCargando(false);
    })();

    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- corre una sola vez por montaje, ver comentario arriba
  }, []);

  const procesarTurno = useCallback(
    async (texto: string) => {
      const faseAntes = faseActualRef.current;
      const fichaAntes = fichaRef.current;

      setMensajes((prev) => [...prev, { rol: "user", texto }]);
      setOpcionesPendientes([]);
      setCargando(true);

      let faseFinal = faseAntes;
      let fichaDespues: FichaSnapshot | null = null;
      const respuesta = await enviarMensaje(texto, idioma);
      for await (const { evento, datos } of leerEventosSSE(respuesta)) {
        if (evento === "mensaje") {
          const d = datos as { fase: number; texto: string; opciones: string[] };
          setMensajes((prev) => [...prev, { rol: "assistant", texto: d.texto }]);
          faseFinal = d.fase;
          setFaseActual(d.fase);
          setOpcionesPendientes(d.opciones);
        } else if (evento === "ficha") {
          fichaDespues = datos as FichaSnapshot;
          setFicha(fichaDespues);
        } else if (evento === "error") {
          console.error("Error del backend:", (datos as { detalle: string }).detalle);
          setMensajes((prev) => [...prev, { rol: "assistant", texto: t.error_generico }]);
        }
      }
      setCargando(false);

      if (!fichaDespues) return;

      // Mismo criterio que _procesar_turno en ui/app.py: festejo solo en
      // un hito real (sistema recién completado, o un check-in cumplido
      // que agregó una versión nueva), nunca en cada mensaje.
      if (faseAntes === 4 && faseFinal === 5) {
        setFestejo({ tipo: "globos" });
        return;
      }
      if (faseAntes === 5 && faseFinal === 5) {
        const totalAntes = fichaAntes ? fichaAntes.historial.length + (fichaAntes.existe ? 1 : 0) : 0;
        const totalDespues = fichaDespues.historial.length + (fichaDespues.existe ? 1 : 0);
        if (totalDespues > totalAntes) {
          const datosNuevos = (fichaDespues.actual?.datos ?? {}) as { cumplido?: boolean };
          if (datosNuevos.cumplido === true) {
            setFestejo({ tipo: "toast", mensaje: t.checkin_toast.replace("{racha}", String(fichaDespues.racha)) });
          }
        }
      }
    },
    [idioma, t],
  );

  const datos = (ficha?.actual?.datos ?? {}) as { proposito?: string; sistema?: string };
  const nombre = ficha?.nombre ?? null;

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar
        idioma={idioma}
        onCambiarIdioma={onCambiarIdioma}
        t={t}
        usuarioId={usuarioId}
        requiereLogin={requiereLogin}
        fase={faseActual}
        ficha={ficha}
      />

      <main className="flex flex-1 flex-col">
        {ficha && !nombre && <BienvenidaCard t={t} />}

        {ficha && (
          <JourneyMap idioma={idioma} t={t} faseActual={faseActual} proposito={datos.proposito} sistema={datos.sistema} />
        )}

        {ficha && faseActual === 5 && <ResumenCard t={t} vistaResumen={ficha.vista_resumen} />}

        {nombre && <p className="px-4 pt-2 text-xs text-foreground/60">{t.saludo_nombre.replace("{nombre}", nombre)}</p>}

        <ChatWindow mensajes={mensajes} cargando={cargando} />

        {opcionesPendientes.length > 0 && (
          <OpcionesForm
            titulo={t.opciones_titulo}
            submitLabel={t.opciones_submit}
            opciones={opcionesPendientes}
            deshabilitado={cargando}
            onElegir={procesarTurno}
          />
        )}

        <ChatInput placeholder={t.chat_placeholder} deshabilitado={cargando} onEnviar={procesarTurno} />
      </main>

      <Celebracion festejo={festejo} onFin={() => setFestejo(null)} />
    </div>
  );
}
