"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { abrirSesion, confirmarSeleccion, continuarSesion, enviarMensaje } from "@/lib/apiCliente";
import { TEXTOS } from "@/lib/i18n";
import { leerEventosSSE } from "@/lib/sse";
import type { CandidatoProposito, FichaSnapshot, Idioma, Mensaje } from "@/lib/types";
import { CabeceraFase } from "./Chat/CabeceraFase";
import { ChatInput } from "./Chat/ChatInput";
import { ChatWindow } from "./Chat/ChatWindow";
import { OpcionesForm } from "./Chat/OpcionesForm";
import { PanelDetalles } from "./Chat/PanelDetalles";
import { EstadoError } from "./EstadoError";
import { ResumenCard } from "./Fase5Summary/ResumenCard";
import { JourneyMap } from "./JourneyMap/JourneyMap";
import type { Festejo } from "./Notifications/Celebracion";
import { Celebracion } from "./Notifications/Celebracion";
import { ArbolSelector } from "./Seleccion/ArbolSelector";
import { SistemaSelector } from "./Seleccion/SistemaSelector";
import { CandidatosProposito } from "./Sintesis/CandidatosProposito";

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

// Fases 0, 1 y 4 nunca renderizan el chat (siempre un selector visual,
// ver esFaseChat más abajo) -- un mensaje de texto que llega para
// alguna de esas fases no tiene dónde mostrarse en esa vista. Bug real
// reportado (14/09/2026): el aviso fijo "¿cómo te llamas?" (fase 0, el
// primer evento de una persona sin nombre guardado) igual se agregaba a
// `mensajes`, invisible mientras se mostraba ArbolSelector -- pero una
// vez que la persona avanzaba a una fase de chat de verdad (Fase 2), el
// historial completo se renderizaba de una, mezclando ese aviso viejo y
// fuera de contexto con la respuesta real del Sintetizador. No agregar
// a `mensajes` un texto que llega para una fase que nunca lo muestra,
// en vez de dejarlo ahí a la espera de una fase de chat futura que lo
// reviva sin contexto.
//
// Fase 3 (Coach de Validación, un selector de evidencia + chat de
// refinado) existía como caso híbrido acá -- se eliminó del flujo del
// todo (pedido explícito del dueño del producto, 14/09/2026: elegir un
// candidato de propósito pasa directo a construir el sistema, sin otra
// ventana ni otro chat en el medio). self.fase_actual ya nunca vale 3
// en una sesión nueva, ver agents/orquestador.py.
function esFaseSoloSelector(fase: number): boolean {
  return fase === 0 || fase === 1 || fase === 4;
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
  // Candidatos de propósito estructurados (Fase 2, ver
  // Sintesis/CandidatosProposito.tsx) -- reemplaza a OpcionesForm para
  // este momento puntual, nunca coexisten (el Sintetizador ya no llama
  // a presentar_opciones, ver agents/sintetizador.py).
  const [candidatosPendientes, setCandidatosPendientes] = useState<CandidatoProposito[]>([]);
  const [faseActual, setFaseActual] = useState(1);
  const [ficha, setFicha] = useState<FichaSnapshot | null>(null);
  // Arranca en true a propósito (no vía setState en el efecto de abajo):
  // este componente se remonta entero cada vez que cambia el idioma
  // (key={idioma} en TelosApp), así que "recién montado" y "cargando la
  // apertura de sesión" son lo mismo.
  const [cargando, setCargando] = useState(true);
  const [festejo, setFestejo] = useState<Festejo | null>(null);
  // Panel de "Detalles" (fase/racha, resultados, evolución, exportar,
  // notificaciones) -- ver Chat/PanelDetalles.tsx. Antes vivía siempre
  // visible en Sidebar.tsx; ahora es a pedido, así el chat no compite
  // por espacio con un panel de resultados todo el tiempo.
  const [detallesAbierto, setDetallesAbierto] = useState(false);

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
          const d = datos as { fase: number; texto: string; opciones: string[]; candidatos: CandidatoProposito[] };
          if (!esFaseSoloSelector(d.fase)) setMensajes((prev) => [...prev, { rol: "assistant", texto: d.texto }]);
          setFaseActual(d.fase);
          setOpcionesPendientes(d.opciones);
          setCandidatosPendientes(d.candidatos);
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
      setCandidatosPendientes([]);
      setCargando(true);

      let faseFinal = faseAntes;
      let fichaDespues: FichaSnapshot | null = null;
      const respuesta = await enviarMensaje(texto, idioma);
      for await (const { evento, datos } of leerEventosSSE(respuesta)) {
        if (evento === "mensaje") {
          const d = datos as { fase: number; texto: string; opciones: string[]; candidatos: CandidatoProposito[] };
          if (!esFaseSoloSelector(d.fase)) setMensajes((prev) => [...prev, { rol: "assistant", texto: d.texto }]);
          faseFinal = d.fase;
          setFaseActual(d.fase);
          setOpcionesPendientes(d.opciones);
          setCandidatosPendientes(d.candidatos);
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

  // Fases 1, 2 (al elegir un candidato de propósito) y 4 cierran por
  // selección visual/tarjeta (ArbolSelector, CandidatosProposito,
  // SistemaSelector), fuera del pipeline de texto de procesarTurno --
  // así que su cascada hacia la fase siguiente nunca se dispara sola.
  // Mismo criterio que agents/orquestador.py::SesionTelos.
  // continuar_tras_seleccion (que es justo lo que este endpoint invoca):
  // se llama una sola vez, después de que el cierre explícito ya guardó
  // la ficha del lado del backend. `mensajeCierre` es el texto que ya
  // dejó ESE cierre (ej. "Ver mi propósito" en Fase 1) -- se muestra acá
  // como el turno previo a la cascada, nunca se descarta en silencio.
  const iniciarFaseSiguiente = useCallback(
    async (mensajeCierre?: string) => {
      setCargando(true);
      if (mensajeCierre) {
        setMensajes((prev) => [...prev, { rol: "assistant", texto: mensajeCierre }]);
      }
      const respuesta = await continuarSesion(idioma);
      for await (const { evento, datos } of leerEventosSSE(respuesta)) {
        if (evento === "mensaje") {
          const d = datos as { fase: number; texto: string; opciones: string[]; candidatos: CandidatoProposito[] };
          if (!esFaseSoloSelector(d.fase)) setMensajes((prev) => [...prev, { rol: "assistant", texto: d.texto }]);
          setFaseActual(d.fase);
          setOpcionesPendientes(d.opciones);
          setCandidatosPendientes(d.candidatos);
        } else if (evento === "ficha") {
          setFicha(datos as FichaSnapshot);
        } else if (evento === "error") {
          console.error("Error del backend:", (datos as { detalle: string }).detalle);
          setMensajes((prev) => [...prev, { rol: "assistant", texto: t.error_generico }]);
        }
      }
      setCargando(false);
    },
    [idioma, t],
  );

  // Elegir una tarjeta de candidato ES el evento de "Fase 2 completa" --
  // no hace falta otro turno de chat para que el Sintetizador "confirme"
  // algo que la interfaz ya sabe con certeza (pedido explícito del dueño
  // del producto, 14/09/2026: la interfaz ya manda los eventos que
  // marcan el paso entre fases). Mismo endpoint determinístico que
  // ArbolSelector/SistemaSelector ya usan (POST /api/seleccion/confirmar,
  // ver agents/orquestador.py::SesionTelos.confirmar_proposito_elegido)
  // -- nunca pasa por enviarMensaje/el Sintetizador de vuelta, y pasa
  // directo a Fase 4 (construir el sistema): Fase 3 (Coach de
  // Validación) se eliminó del flujo. "Combinar partes de varios" sigue
  // siendo texto libre por el ChatInput de siempre, sin pasar por acá --
  // esta función es solo para el click directo en una tarjeta.
  const elegirProposito = useCallback(
    async (frase: string) => {
      setCandidatosPendientes([]);
      setCargando(true);
      try {
        const resultado = await confirmarSeleccion({ fase: 2, nodoId: frase, idioma });
        if (resultado.cerrado) {
          await iniciarFaseSiguiente(resultado.mensaje_cierre ?? undefined);
        } else {
          setCargando(false);
        }
      } catch (e) {
        console.error("No se pudo confirmar el propósito elegido:", e);
        setMensajes((prev) => [...prev, { rol: "assistant", texto: t.error_generico }]);
        setCargando(false);
      }
    },
    [idioma, t, iniciarFaseSiguiente],
  );

  const datos = (ficha?.actual?.datos ?? {}) as { proposito?: string; sistema?: string };
  const nombre = ficha?.nombre ?? null;

  // Fases con selector visual propio (0, 1, 4): la sidebar se oculta y
  // el selector ocupa todo el viewport -- su propio fondo y tipografía
  // warm reemplazan el chrome de la app. En fases de chat (2, 5) la
  // sidebar vuelve a mostrarse.
  // Nota: nombre puede ser null en el primer login (se obtiene dentro del
  // flujo de Fase 1) -- no lo usamos como prerequisito para mostrar los
  // selectores visuales.
  //
  // `esFaseChat` es la única condición que decide la sidebar y la rama
  // de chat/dashboard -- a propósito NO es "cualquier fase que no sea
  // selector" (`!esSelector`): esa forma de escribirlo fue justo el bug
  // real (13/09/2026) que hizo que fase 0 cayera en el dashboard de chat
  // con "Propósito"/"Sistema" vacíos, porque un valor de fase no
  // contemplado en el chequeo de selector caía por descarte en la rama
  // de chat en vez de marcarse como el error que era. Listando ambas
  // condiciones en positivo, cualquier fase que no matchee ninguna de
  // las dos (no debería pasar nunca en uso normal) cae explícitamente en
  // EstadoError más abajo, nunca en un dashboard vacío que se ve
  // legítimo sin serlo.
  const esFaseChat = faseActual === 2 || faseActual === 5;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Fases 1 y 4: la interfaz principal deja de ser el chat --
          selector visual, con el chat relegado a apoyo opcional (Fase 1).
          El resto de las fases (2, 5) es chat, pero con la MISMA
          cabecera visual que estos dos selectores (ver CabeceraFase) en
          vez del panel de resultados que antes ocupaba toda la altura --
          pedido explícito del dueño del producto: las fases de chat
          tienen que sentirse la misma aplicación, no una pantalla
          intermedia aparte. Cualquier otro valor de fase (no debería
          pasar nunca en uso normal) cae en EstadoError, no en el chat --
          ver comentario de esFaseChat arriba. */}
      {(faseActual === 0 || faseActual === 1) ? (
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <ArbolSelector idioma={idioma} onCambiarIdioma={onCambiarIdioma} requiereLogin={requiereLogin} nombre={nombre} onCerrado={iniciarFaseSiguiente} />
        </main>
      ) : faseActual === 4 ? (
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <SistemaSelector idioma={idioma} onCambiarIdioma={onCambiarIdioma} requiereLogin={requiereLogin} proposito={datos.proposito} onCerrado={iniciarFaseSiguiente} />
        </main>
      ) : esFaseChat ? (
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <CabeceraFase
            idioma={idioma}
            onCambiarIdioma={onCambiarIdioma}
            t={t}
            usuarioId={usuarioId}
            requiereLogin={requiereLogin}
            proposito={datos.proposito}
            sistema={datos.sistema}
            onAbrirDetalles={() => setDetallesAbierto(true)}
          />

          <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {ficha && (
              <JourneyMap idioma={idioma} t={t} faseActual={faseActual} proposito={datos.proposito} sistema={datos.sistema} />
            )}

            {ficha && faseActual === 5 && <ResumenCard t={t} proposito={datos.proposito} sistema={datos.sistema} />}

            {nombre && <p className="px-4 pt-2 text-xs text-foreground/60">{t.saludo_nombre.replace("{nombre}", nombre)}</p>}

            <ChatWindow mensajes={mensajes} cargando={cargando} />

            {candidatosPendientes.length > 0 ? (
              <CandidatosProposito
                idioma={idioma}
                candidatos={candidatosPendientes}
                deshabilitado={cargando}
                onElegir={elegirProposito}
              />
            ) : (
              opcionesPendientes.length > 0 && (
                <OpcionesForm
                  titulo={t.opciones_titulo}
                  submitLabel={t.opciones_submit}
                  opciones={opcionesPendientes}
                  deshabilitado={cargando}
                  onElegir={procesarTurno}
                />
              )
            )}

            <ChatInput placeholder={t.chat_placeholder} deshabilitado={cargando} onEnviar={procesarTurno} />
          </main>

          {detallesAbierto && (
            <PanelDetalles idioma={idioma} t={t} fase={faseActual} ficha={ficha} onCerrar={() => setDetallesAbierto(false)} />
          )}
        </div>
      ) : (
        <EstadoError t={t} />
      )}

      <Celebracion festejo={festejo} onFin={() => setFestejo(null)} />
    </div>
  );
}
