"use client";

import { useEffect, useState } from "react";

import { confirmarSeleccion, continuarSesion, obtenerCategoriasFase4 } from "@/lib/apiCliente";
import type { CategoriasFase4, Idioma, NodoCategoriaSistema } from "@/lib/types";
import { AccionesCuenta } from "../AccionesCuenta";

// Selector visual de Fase 4 (Estratega de Sistemas) -- porte fiel del
// prototipo interactivo real hecho en Claude Design (13/09/2026, mismo
// criterio que ArbolSelector.tsx para Fase 1: se adopta el diseño tal
// cual, no una construcción propia sobre el brief). El backend
// (agents/orquestador.py::SesionTelos.confirmar_seleccion_sistema +
// tools/categorias_sistema.py) ya trae el contenido y la mecánica de ese
// prototipo -- este componente es la traducción a React real, cableada a
// los endpoints verdaderos en vez del estado local del mockup.
//
// Diferencia deliberada respecto al prototipo: la pantalla de cierre
// ("isDone") ahí tenía links "ajustar" para reabrir cualquier respuesta y
// un botón para reiniciar la demo. Acá, para cuando esa pantalla se
// muestra, Fase 4 YA cerró de verdad en el backend (fase_actual pasó a
// 5) -- reabrir una respuesta ya no es una operación válida
// (confirmar_seleccion_sistema rechaza fuera de fase 4), así que el
// cierre es un resumen de solo lectura con un único botón que continúa
// hacia Fase 5 (mismo patrón que ArbolSelector.verMiProposito).
//
// El chat de apoyo es autocontenido con respuestas guiadas fijas (igual
// que el prototipo) -- acá las dudas son sobre CÓMO elegir una opción de
// una lista ya fija, no sobre encontrar una categoría inexistente en un
// árbol grande (ese es el problema que sí tiene Fase 1, resuelto en
// ArbolSelector vía agents/asistente_categorias.py), así que no hace
// falta un backend real para esto.

type Nivel = "top" | "sub" | "plan";

type Respuesta = { nodo_id: string; label: string; ruta: string[]; detalle_libre: string | null };

const ACENTO = "#a4552f";
const PASOS = ["accion", "cuando_donde", "metrica", "obstaculo"] as const;

const TEXTOS = {
  es: {
    faseLabel: "Fase 4 · Estratega de sistemas",
    cerrarSesion: "Cerrar sesión",
    ayudaChat: "¿Necesitas aclarar algo?",
    cerrarApoyo: "Cerrar apoyo",
    apoyoTitulo: "Apoyo",
    apoyoSub: "Pregunta lo que necesites aclarar",
    chatPlaceholder: "Escribe tu duda…",
    propositoValidado: "Propósito validado",
    demosleForma: "Démosle una forma práctica.",
    introBuilding: "Cuatro decisiones cortas: qué vas a repetir, cuándo y dónde, cómo lo mides y qué harás cuando algo lo saque de curso.",
    construirSistema: "Construir mi sistema",
    volver: "← Volver",
    cerrarSistema: "Cerrar el sistema",
    planPlaceholder: "¿Qué harás cuando aparezca? (opcional)",
    stepCounter: (n: number) => `Paso ${n} de 4`,
    stepLabels: ["Acción", "Cuándo", "Métrica", "Obstáculo"],
    ajustar: "ajustar",
    niveles: {
      cat: { label: "Paso 1 · Acción", title: "¿Qué vas a realizar?", sub: "Elige el terreno. Después bajamos a lo concreto." },
      item: (cat: string) => ({ label: `Paso 1 · Acción · ${cat}`, title: "Más concreto: ¿qué exactamente?", sub: "Una sola cosa. La que puedas repetir sin negociar contigo cada vez." }),
      moment: { label: "Paso 2 · Cuándo y dónde", title: "¿Cuándo y dónde va a ocurrir?", sub: "Primero el momento del día donde esto puede vivir." },
      context: (m: string) => ({ label: `Paso 2 · Cuándo y dónde · ${m}`, title: "¿Con qué frecuencia, y en qué lugar?", sub: "Elige el contexto más realista, no el más ambicioso." }),
      metric: { label: "Paso 3 · Métrica", title: "¿Cómo sabrás que lo cumpliste?", sub: "Una sola señal, clara al terminar el día." },
      obsCat: { label: "Paso 4 · Obstáculo", title: "¿Qué puede sacar al sistema de su curso?", sub: "No es pesimismo: es tener la respuesta lista de antemano." },
      obsItem: (cat: string) => ({ label: `Paso 4 · Obstáculo · ${cat}`, title: "¿De qué forma aparece?", sub: "Cuanto más preciso, más fácil es responderle." }),
      plan: (cat: string) => ({ label: `Paso 4 · Obstáculo · ${cat}`, title: "Y cuando aparezca, ¿qué harás?", sub: "Opcional. Si lo dejas vacío, Telos propone una respuesta mínima por ti." }),
    },
    trailKind: { accion: "Acción", cuando_donde: "Cuándo", metrica: "Métrica" } as Record<string, string>,
    done: {
      kicker: "Fase 4 · completa",
      kickerSub: "Cuatro piezas, un solo sistema",
      cuando: "Cuándo",
      accion: "Acción",
      metrica: "Métrica",
      tuSistema: "Tu sistema",
      siAparece: "Si aparece",
      planPorDefectoAviso: "Telos propuso un plan mínimo para este caso.",
      closingLine: "Una forma concreta de llevar tu propósito a tu vida cotidiana.",
      proximaVez: "La próxima vez no empezaremos de cero.",
      veremos: "Veremos cómo está funcionando este sistema en tu vida real.",
      continuar: "Seguir",
    },
    sugerencias: ["¿Qué significa esta opción?", "¿Cuál debería elegir?", "¿En qué se diferencian?"],
    mensajeInicialChat: "Esta fase solo convierte tu propósito en algo repetible. Si dudas entre dos opciones, elige la que podrías sostener en una semana difícil.",
    error: "No se pudo guardar. Probá de nuevo.",
    errorCarga: "No se pudo cargar. Recargá la página.",
  },
  en: {
    faseLabel: "Phase 4 · Systems strategist",
    cerrarSesion: "Sign out",
    ayudaChat: "Need something clarified?",
    cerrarApoyo: "Close support",
    apoyoTitulo: "Support",
    apoyoSub: "Ask whatever you need clarified",
    chatPlaceholder: "Type your question…",
    propositoValidado: "Validated purpose",
    demosleForma: "Let's give it a practical shape.",
    introBuilding: "Four short decisions: what you'll repeat, when and where, how you measure it, and what you'll do when something throws it off.",
    construirSistema: "Build my system",
    volver: "← Back",
    cerrarSistema: "Close the system",
    planPlaceholder: "What will you do when it shows up? (optional)",
    stepCounter: (n: number) => `Step ${n} of 4`,
    stepLabels: ["Action", "When", "Metric", "Obstacle"],
    ajustar: "adjust",
    niveles: {
      cat: { label: "Step 1 · Action", title: "What will you do?", sub: "Pick the terrain. We'll get concrete after." },
      item: (cat: string) => ({ label: `Step 1 · Action · ${cat}`, title: "More specific: what exactly?", sub: "One single thing. One you can repeat without negotiating with yourself each time." }),
      moment: { label: "Step 2 · When & where", title: "When and where will it happen?", sub: "First, the time of day this can live in." },
      context: (m: string) => ({ label: `Step 2 · When & where · ${m}`, title: "How often, and where?", sub: "Pick the most realistic context, not the most ambitious." }),
      metric: { label: "Step 3 · Metric", title: "How will you know you kept it?", sub: "One single signal, clear by the end of the day." },
      obsCat: { label: "Step 4 · Obstacle", title: "What could throw the system off course?", sub: "It's not pessimism: it's having the answer ready ahead of time." },
      obsItem: (cat: string) => ({ label: `Step 4 · Obstacle · ${cat}`, title: "How does it show up?", sub: "The more precise, the easier it is to respond to." }),
      plan: (cat: string) => ({ label: `Step 4 · Obstacle · ${cat}`, title: "And when it shows up, what will you do?", sub: "Optional. If you leave it blank, Telos proposes a minimal answer for you." }),
    },
    trailKind: { accion: "Action", cuando_donde: "When", metrica: "Metric" } as Record<string, string>,
    done: {
      kicker: "Phase 4 · complete",
      kickerSub: "Four pieces, one system",
      cuando: "When",
      accion: "Action",
      metrica: "Metric",
      tuSistema: "Your system",
      siAparece: "If it shows up",
      planPorDefectoAviso: "Telos proposed a minimal plan for this case.",
      closingLine: "A concrete way to bring your purpose into your everyday life.",
      proximaVez: "Next time we won't start from zero.",
      veremos: "We'll see how this system is working in your real life.",
      continuar: "Continue",
    },
    sugerencias: ["What does this option mean?", "Which should I choose?", "How are these different?"],
    mensajeInicialChat: "This phase just turns your purpose into something repeatable. If you're torn between two options, pick the one you could sustain through a hard week.",
    error: "Couldn't save. Try again.",
    errorCarga: "Couldn't load. Reload the page.",
  },
} as const;

function respuestaMecanica(bajo: string, idioma: Idioma): string | null {
  if (idioma === "es") {
    if (bajo.includes("signif")) return "Cada tarjeta describe una forma concreta de repetir algo. Si no te imaginas haciéndola el martes a la hora elegida, probablemente no es esa.";
    if (bajo.includes("difer")) return "La diferencia está en cómo se verifica: una cantidad se cuenta, un sí o no se responde en un segundo, algo terminado se ve.";
    if (bajo.includes("deber") || bajo.includes("cuál") || bajo.includes("cual")) return "Empieza por la versión más pequeña que siga siendo verdadera para ti. Es más fácil subir la exigencia que reconstruir el hábito.";
    if (bajo.includes("obst")) return "El obstáculo no se elige por miedo, se elige por historial: piensa en la última vez que algo así se cayó y por qué.";
    return "Elige la opción que puedas sostener una semana mala, no la mejor semana posible. Todo se puede ajustar después con \"Volver\".";
  }
  if (bajo.includes("mean")) return "Each card describes a concrete way to repeat something. If you can't picture doing it on Tuesday at the chosen time, it's probably not the one.";
  if (bajo.includes("differ")) return "The difference is in how it gets verified: a quantity gets counted, a yes/no gets answered in a second, something finished gets seen.";
  if (bajo.includes("should") || bajo.includes("which")) return "Start with the smallest version that's still true to you. It's easier to raise the bar than to rebuild the habit.";
  if (bajo.includes("obstacle")) return "You don't pick the obstacle out of fear, you pick it from history: think about the last time something like this fell through, and why.";
  return "Pick the option you could sustain through a bad week, not your best possible week. Everything can be adjusted later with \"Back\".";
}

function labelDeNodo(arbol: NodoCategoriaSistema[], id: string): string {
  for (const n of arbol) {
    if (n.id === id) return n.label;
    if (n.hijos) {
      const enHijos = labelDeNodo(n.hijos, id);
      if (enHijos) return enHijos;
    }
  }
  return "";
}

export function SistemaSelector({
  idioma,
  onCambiarIdioma,
  requiereLogin,
  proposito,
  onCerrado,
}: {
  idioma: Idioma;
  onCambiarIdioma: (idioma: Idioma) => void;
  requiereLogin: boolean;
  proposito?: string;
  onCerrado: (mensajeCierre?: string) => void;
}) {
  const t = TEXTOS[idioma];

  const [taxonomia, setTaxonomia] = useState<CategoriasFase4 | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [started, setStarted] = useState(false);
  const [paso, setPaso] = useState(0); // índice en PASOS
  const [nivel, setNivel] = useState<Nivel>("top");
  const [categoriaId, setCategoriaId] = useState<string | null>(null); // paso 0
  const [momentoId, setMomentoId] = useState<string | null>(null); // paso 1
  const [obsCatId, setObsCatId] = useState<string | null>(null); // paso 3
  const [obsItemId, setObsItemId] = useState<string | null>(null); // paso 3
  const [plan, setPlan] = useState("");

  const [respuestas, setRespuestas] = useState<Record<string, Respuesta>>({});
  const [done, setDone] = useState(false);
  const [mensajeCierre, setMensajeCierre] = useState<string | undefined>(undefined);
  const [guardando, setGuardando] = useState(false);
  const [continuando, setContinuando] = useState(false);

  const [chatOpen, setChatOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<{ who: "me" | "bot"; text: string }[]>([{ who: "bot", text: t.mensajeInicialChat }]);

  useEffect(() => {
    let cancelado = false;
    obtenerCategoriasFase4(idioma)
      .then((d) => {
        if (!cancelado) setTaxonomia(d);
      })
      .catch(() => {
        if (!cancelado) setError(t.errorCarga);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- t depende de idioma, ya cubierto
  }, [idioma]);

  if (error && !taxonomia)
    return (
      <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", padding: 32, textAlign: "center", fontSize: 13.5, color: "#6b6459" }}>
        {error}
      </div>
    );
  if (!taxonomia)
    return (
      <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", fontSize: 13, color: "#a8a096" }}>
        …
      </div>
    );

  const preguntaId = PASOS[paso];
  const arbolPaso = taxonomia.categorias[preguntaId] ?? [];

  // ---------- nivel efectivo (mismo estado (paso,nivel) que el prototipo) ----------

  type Clave = "cat" | "item" | "moment" | "context" | "metric" | "obsCat" | "obsItem" | "plan";

  function clave(): Clave {
    if (paso === 0) return nivel === "top" ? "cat" : "item";
    if (paso === 1) return nivel === "top" ? "moment" : "context";
    if (paso === 2) return "metric";
    if (nivel === "plan") return "plan";
    return nivel === "top" ? "obsCat" : "obsItem";
  }

  const k = clave();

  function opcionesActuales(): NodoCategoriaSistema[] {
    if (k === "cat" || k === "moment" || k === "metric" || k === "obsCat") return arbolPaso;
    if (k === "item") return arbolPaso.find((c) => c.id === categoriaId)?.hijos ?? [];
    if (k === "context") return arbolPaso.find((m) => m.id === momentoId)?.hijos ?? [];
    if (k === "obsItem") return arbolPaso.find((c) => c.id === obsCatId)?.hijos ?? [];
    return [];
  }

  function encabezado(): { label: string; title: string; sub: string } {
    if (k === "cat") return t.niveles.cat;
    if (k === "item") return t.niveles.item(labelDeNodo(arbolPaso, categoriaId ?? ""));
    if (k === "moment") return t.niveles.moment;
    if (k === "context") return t.niveles.context(labelDeNodo(arbolPaso, momentoId ?? ""));
    if (k === "metric") return t.niveles.metric;
    if (k === "obsCat") return t.niveles.obsCat;
    if (k === "obsItem") return t.niveles.obsItem(labelDeNodo(arbolPaso, obsCatId ?? ""));
    return t.niveles.plan(labelDeNodo(arbolPaso, obsCatId ?? ""));
  }

  async function confirmar(preguntaConfirmar: (typeof PASOS)[number], nodoId: string, detalleLibre?: string) {
    setGuardando(true);
    setError(null);
    try {
      const resultado = await confirmarSeleccion({ fase: 4, preguntaId: preguntaConfirmar, nodoId, idioma, detalleLibre });
      const nuevasRespuestas = (resultado.respuestas ?? {}) as Record<string, Respuesta>;
      setRespuestas(nuevasRespuestas);
      if (resultado.cerrado) {
        setDone(true);
        setMensajeCierre(resultado.mensaje_cierre ?? undefined);
      } else {
        setPaso((p) => p + 1);
        setNivel("top");
      }
    } catch {
      setError(t.error);
    } finally {
      setGuardando(false);
    }
  }

  function elegir(id: string) {
    if (guardando) return;
    if (k === "cat") {
      setCategoriaId(id);
      setNivel("sub");
    } else if (k === "item") {
      confirmar("accion", id);
    } else if (k === "moment") {
      setMomentoId(id);
      setNivel("sub");
    } else if (k === "context") {
      confirmar("cuando_donde", id);
    } else if (k === "metric") {
      confirmar("metrica", id);
    } else if (k === "obsCat") {
      setObsCatId(id);
      setNivel("sub");
    } else if (k === "obsItem") {
      setObsItemId(id);
      setNivel("plan");
    }
  }

  function cerrarSistema() {
    if (!obsItemId) return;
    confirmar("obstaculo", obsItemId, plan.trim() || undefined);
  }

  function volver() {
    if (k === "item") setNivel("top");
    else if (k === "moment") {
      setPaso(0);
      setNivel("sub");
    } else if (k === "context") setNivel("top");
    else if (k === "metric") {
      setPaso(1);
      setNivel("sub");
    } else if (k === "obsCat") {
      setPaso(2);
      setNivel("top");
    } else if (k === "obsItem") setNivel("top");
    else if (k === "plan") setNivel("sub");
    else setStarted(false);
  }

  function irATrail(kind: string) {
    if (kind === "accion") {
      setPaso(0);
      setNivel("sub");
    } else if (kind === "cuando_donde") {
      setPaso(1);
      setNivel("sub");
    } else if (kind === "metrica") {
      setPaso(2);
      setNivel("top");
    }
  }

  async function continuar() {
    setContinuando(true);
    try {
      await continuarSesion(idioma).catch(() => {});
      onCerrado(mensajeCierre);
    } finally {
      setContinuando(false);
    }
  }

  function respuestaMecanicaOEnviar(texto: string) {
    const limpio = texto.trim();
    if (!limpio) return;
    const respuesta = respuestaMecanica(limpio.toLowerCase(), idioma);
    setMessages((prev) => [...prev, { who: "me", text: limpio }, { who: "bot", text: respuesta ?? "" }]);
    setDraft("");
  }

  const trail = PASOS.filter((p, i) => i < paso && respuestas[p] && p !== "obstaculo").map((p) => ({
    kind: p,
    label: t.trailKind[p],
    value: respuestas[p].label,
  }));

  const encabezadoActual = started && !done ? encabezado() : null;

  return (
    <div
      style={{
        height: "100%",
        minHeight: 0,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        background: "radial-gradient(70% 45% at 50% 0%, rgba(226,164,74,.13) 0%, rgba(226,164,74,0) 60%), linear-gradient(#fcfaf7 0%, #f5f1ea 55%, #efe8dd 100%)",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
        position: "relative",
      }}
    >
      <style>{`
        @keyframes telos-rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
        @keyframes telos-fade { from { opacity:0; } to { opacity:1; } }
        @keyframes telos-breathe { 0%,100% { opacity:.55; transform:scale(1); } 50% { opacity:.85; transform:scale(1.035); } }
      `}</style>

      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 18, padding: "16px clamp(18px,5vw,56px) 8px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/telos-brand.png" alt="TelOS" style={{ width: 32, height: 32, borderRadius: 9, objectFit: "cover", objectPosition: "50% 34%", background: "#1d1b33", flexShrink: 0 }} />
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 12.5, letterSpacing: ".34em", textTransform: "uppercase" }}>Telos</span>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: "#6b6459" }}>{t.faseLabel}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "clamp(10px,2vw,20px)", flexWrap: "wrap" }}>
          <button
            onClick={() => setChatOpen((v) => !v)}
            style={{ display: "flex", alignItems: "center", gap: 9, border: "1px solid #ded7cc", background: "rgba(252,250,247,.8)", color: "#5d564d", borderRadius: 999, padding: "8px 15px", fontSize: 12.5, cursor: "pointer" }}
          >
            <span style={{ width: 7, height: 7, borderRadius: 999, background: ACENTO, animation: "telos-breathe 3.4s ease-in-out infinite" }} />
            <span>{chatOpen ? t.cerrarApoyo : t.ayudaChat}</span>
          </button>

          <AccionesCuenta idioma={idioma} onCambiarIdioma={onCambiarIdioma} requiereLogin={requiereLogin} logoutLabel={t.cerrarSesion} />
        </div>
      </header>

      {started && !done && (
        <div style={{ display: "flex", alignItems: "center", gap: "clamp(10px,2vw,22px)", flexWrap: "wrap", padding: "6px clamp(18px,5vw,56px) 0", maxWidth: 1080, width: "100%", margin: "0 auto" }}>
          {t.stepLabels.map((label, i) => (
            <button
              key={label}
              onClick={() => {
                if (paso > i) {
                  setPaso(i);
                  setNivel("top");
                }
              }}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 6,
                minWidth: 92,
                flex: 1,
                background: "transparent",
                border: "none",
                padding: "2px 0 0",
                cursor: paso > i ? "pointer" : "default",
                textAlign: "left",
              }}
            >
              <span style={{ display: "flex", alignItems: "baseline", gap: 7, fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: paso === i ? "#1b1917" : paso > i ? "#8c8478" : "#b7afa4" }}>
                <span>{"0" + (i + 1)}</span>
                <span>{label}</span>
              </span>
              <span style={{ height: 2, width: "100%", background: paso === i ? ACENTO : paso > i ? "#c9bfb0" : "#e4ddd2", transition: "background .5s ease" }} />
            </button>
          ))}
          <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: "#b0a79a", flex: "none" }}>{t.stepCounter(paso + 1)}</span>
        </div>
      )}

      <main style={{ flex: 1, width: "100%", maxWidth: 1080, margin: "0 auto", padding: "clamp(20px,5vh,56px) clamp(18px,5vw,56px) 40px", display: "flex", flexDirection: "column", gap: "clamp(18px,3vh,30px)" }}>
        {!started && !done && (
          <section style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 660, animation: "telos-rise .7s ease both" }}>
            <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: ACENTO }}>{t.propositoValidado}</span>
            {proposito && <p style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(24px,3.2vw,40px)", lineHeight: 1.16 }}>{proposito}</p>}
            <div style={{ height: 1, background: "#e2dbd0" }} />
            <h1 style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontWeight: 400, fontSize: "clamp(20px,2.4vw,28px)", lineHeight: 1.2 }}>{t.demosleForma}</h1>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "#5d564d", maxWidth: "52ch" }}>{t.introBuilding}</p>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", paddingTop: 4 }}>
              <button onClick={() => setStarted(true)} style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "14px 28px", fontSize: 14.5, cursor: "pointer" }}>
                {t.construirSistema}
              </button>
            </div>
          </section>
        )}

        {started && !done && encabezadoActual && (
          <section style={{ display: "flex", flexDirection: "column", gap: "clamp(16px,2.5vh,26px)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 640, animation: "telos-fade .5s ease both" }}>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase", color: ACENTO }}>{encabezadoActual.label}</span>
              <h2 style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontWeight: 400, fontSize: "clamp(26px,3.4vw,42px)", lineHeight: 1.13 }}>{encabezadoActual.title}</h2>
              <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.55, color: "#6b6459", maxWidth: "48ch" }}>{encabezadoActual.sub}</p>
            </div>

            {error && <p style={{ margin: 0, fontSize: 12.5, color: "#b3261e" }}>{error}</p>}

            {trail.length > 0 && (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                {trail.map((chip) => (
                  <button
                    key={chip.kind}
                    onClick={() => irATrail(chip.kind)}
                    style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid #e2dbd0", background: "#fcfaf7", borderRadius: 999, padding: "5px 12px", fontSize: 12.5, color: "#3b3630", cursor: "pointer" }}
                  >
                    <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9, letterSpacing: ".14em", textTransform: "uppercase", color: "#a09689" }}>{chip.label}</span>
                    <span>{chip.value}</span>
                  </button>
                ))}
              </div>
            )}

            {k !== "plan" && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 224px), 1fr))", gap: "clamp(9px,1.2vw,14px)" }}>
                {opcionesActuales().map((opt, i) => (
                  <button
                    key={opt.id}
                    disabled={guardando}
                    onClick={() => elegir(opt.id)}
                    style={{
                      position: "relative",
                      textAlign: "left",
                      display: "flex",
                      flexDirection: "column",
                      gap: 7,
                      minHeight: 96,
                      border: "1px solid #e6ddd0",
                      background: "#fcfaf7",
                      borderRadius: 16,
                      padding: "16px 17px 18px",
                      cursor: guardando ? "default" : "pointer",
                      opacity: guardando ? 0.6 : 1,
                      animation: "telos-rise .5s ease both",
                      animationDelay: `${i * 40}ms`,
                    }}
                  >
                    <span style={{ fontSize: 16, lineHeight: 1.25 }}>{opt.label}</span>
                    {opt.desc && <span style={{ fontSize: 12.5, lineHeight: 1.45, color: "#7c7568" }}>{opt.desc}</span>}
                  </button>
                ))}
              </div>
            )}

            {k === "plan" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 680, animation: "telos-rise .5s ease both" }}>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", border: "1px solid #e2dbd0", background: "#fcfaf7", borderRadius: 16, padding: "14px 16px" }}>
                  <input
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    placeholder={t.planPlaceholder}
                    style={{ flex: 1, minWidth: 220, border: "none", background: "transparent", outline: "none", fontSize: 14.5, color: "#1b1917" }}
                  />
                  <button
                    onClick={cerrarSistema}
                    disabled={guardando}
                    style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "11px 22px", fontSize: 13, cursor: "pointer", opacity: guardando ? 0.6 : 1 }}
                  >
                    {t.cerrarSistema}
                  </button>
                </div>
              </div>
            )}

            <div>
              <button onClick={volver} style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "9px 18px", fontSize: 12.5, cursor: "pointer" }}>
                {t.volver}
              </button>
            </div>
          </section>
        )}

        {done && (
          <section style={{ display: "flex", flexDirection: "column", gap: "clamp(20px,3vh,32px)", animation: "telos-rise .7s ease both" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 12, flexWrap: "wrap", fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase" }}>
              <span style={{ color: ACENTO }}>{t.done.kicker}</span>
              <span style={{ color: "#6b6459" }}>{t.done.kickerSub}</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 0, padding: "clamp(4px,1.5vh,18px) 0 0" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 5, textAlign: "center", maxWidth: 280 }}>
                <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>{t.done.cuando}</span>
                <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(18px,1.9vw,23px)", lineHeight: 1.2 }}>{respuestas.cuando_donde?.label ?? "—"}</span>
              </div>

              <div style={{ width: 1, height: "clamp(26px,5vh,52px)", background: "#d8cfc2" }} />

              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0, flexWrap: "wrap", width: "100%" }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 5, textAlign: "right", flex: "1 1 180px", minWidth: 150 }}>
                  <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>{t.done.accion}</span>
                  <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(19px,2.1vw,26px)", lineHeight: 1.18 }}>{respuestas.accion?.label ?? "—"}</span>
                </div>

                <div style={{ height: 1, width: "clamp(22px,4vw,58px)", background: "#d8cfc2", flex: "none" }} />

                <div
                  style={{
                    flex: "none",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 9,
                    textAlign: "center",
                    width: "clamp(206px,25vw,268px)",
                    aspectRatio: "1/1",
                    border: "1px solid #ddd3c5",
                    borderRadius: 999,
                    background: "radial-gradient(75% 75% at 50% 40%, rgba(164,85,47,.10) 0%, rgba(252,250,247,1) 72%)",
                    padding: 20,
                  }}
                >
                  <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".26em", textTransform: "uppercase", color: ACENTO }}>{t.done.tuSistema}</span>
                  {proposito && <span style={{ fontSize: 12.5, lineHeight: 1.45, color: "#5d564d" }}>{proposito}</span>}
                </div>

                <div style={{ height: 1, width: "clamp(22px,4vw,58px)", background: "#d8cfc2", flex: "none" }} />

                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 5, flex: "1 1 180px", minWidth: 150 }}>
                  <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>{t.done.metrica}</span>
                  <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(19px,2.1vw,26px)", lineHeight: 1.18 }}>{respuestas.metrica?.label ?? "—"}</span>
                </div>
              </div>

              <div style={{ width: 1, height: "clamp(26px,5vh,52px)", background: "linear-gradient(#d8cfc2, #cdbfa9)" }} />

              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 9, textAlign: "center", border: "1px dashed #cdbfa9", borderRadius: 18, padding: "16px 22px 18px", maxWidth: 440, background: "rgba(252,250,247,.7)" }}>
                <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".2em", textTransform: "uppercase", color: "#6b6459" }}>{t.done.siAparece}</span>
                <span style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(17px,1.8vw,22px)", lineHeight: 1.2, color: "#6b6459" }}>{respuestas.obstaculo?.label ?? "—"}</span>
                <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 13, color: "#8c8478" }}>↓</span>
                <span style={{ fontSize: 14.5, lineHeight: 1.45 }}>{respuestas.obstaculo?.detalle_libre || t.done.planPorDefectoAviso}</span>
              </div>
            </div>

            <p style={{ margin: "0 auto", maxWidth: "46ch", textAlign: "center", fontSize: 14, lineHeight: 1.6, color: "#5d564d" }}>{t.done.closingLine}</p>

            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, borderTop: "1px solid #e2dbd0", paddingTop: "clamp(16px,2.5vh,26px)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                <span style={{ width: 9, height: 9, borderRadius: 999, background: ACENTO, flex: "none" }} />
                <span style={{ height: 1, width: "clamp(34px,7vw,72px)", background: "#d8cfc2" }} />
                <span style={{ width: 9, height: 9, borderRadius: 999, border: "1px solid #c9bfb0", background: "#f5f1ea", flex: "none", animation: "telos-breathe 3.6s ease-in-out infinite" }} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, textAlign: "center", maxWidth: "44ch" }}>
                <span style={{ fontSize: 14, lineHeight: 1.5 }}>{t.done.proximaVez}</span>
                <span style={{ fontSize: 13.5, lineHeight: 1.5, color: "#5d564d" }}>{t.done.veremos}</span>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" }}>
              <button
                onClick={continuar}
                disabled={continuando}
                style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "12px 26px", fontSize: 13.5, cursor: "pointer", opacity: continuando ? 0.6 : 1 }}
              >
                {t.done.continuar}
              </button>
            </div>
          </section>
        )}
      </main>

      {chatOpen && (
        <aside style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(384px,100%)", zIndex: 50, background: "#fcfaf7", borderLeft: "1px solid #e2dbd0", display: "flex", flexDirection: "column", boxShadow: "-30px 0 60px -50px rgba(27,25,23,.7)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "16px 18px", borderBottom: "1px solid #ece6dc" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".18em", textTransform: "uppercase", color: ACENTO }}>{t.apoyoTitulo}</span>
              <span style={{ fontSize: 14 }}>{t.apoyoSub}</span>
            </div>
            <button onClick={() => setChatOpen(false)} style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", width: 30, height: 30, borderRadius: 999, cursor: "pointer", fontSize: 14, lineHeight: 1 }}>
              ×
            </button>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "16px 18px", display: "flex", flexDirection: "column", gap: 12 }}>
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  maxWidth: "88%",
                  alignSelf: m.who === "me" ? "flex-end" : "flex-start",
                  background: m.who === "me" ? "#1b1917" : "#f4f1ec",
                  color: m.who === "me" ? "#f7f4ef" : "#3b3630",
                  border: `1px solid ${m.who === "me" ? "#1b1917" : "#e8e1d7"}`,
                  borderRadius: 14,
                  padding: "11px 14px",
                  fontSize: 13.5,
                  lineHeight: 1.5,
                }}
              >
                {m.text}
              </div>
            ))}
          </div>
          <div style={{ padding: "10px 18px 16px", borderTop: "1px solid #ece6dc", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              {t.sugerencias.map((s) => (
                <button
                  key={s}
                  onClick={() => respuestaMecanicaOEnviar(s)}
                  style={{ border: "1px solid #e2dbd0", background: "transparent", color: "#6b6459", borderRadius: 999, padding: "6px 12px", fontSize: 11.5, cursor: "pointer" }}
                >
                  {s}
                </button>
              ))}
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", border: "1px solid #e2dbd0", borderRadius: 999, padding: "6px 6px 6px 14px" }}>
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") respuestaMecanicaOEnviar(draft);
                }}
                placeholder={t.chatPlaceholder}
                style={{ flex: 1, border: "none", background: "transparent", outline: "none", fontSize: 13.5, color: "#1b1917" }}
              />
              <button onClick={() => respuestaMecanicaOEnviar(draft)} style={{ border: "none", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, width: 32, height: 32, cursor: "pointer", fontSize: 13 }}>
                →
              </button>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
