"use client";

import { useEffect, useMemo, useState } from "react";

import { cerrarFase1, confirmarSeleccion, confirmarValores, obtenerCategoriasFase1 } from "@/lib/apiCliente";
import type { CategoriasFase1, HojaIkigai, Idioma, VerboIkigai } from "@/lib/types";

// Selector visual Ikigai -- Fase 1. Interfaz principal (no un chatbot):
// contenido y mecánica portados del prototipo interactivo real hecho en
// Claude Design (13/09/2026) -- no una construcción propia sobre el
// brief, ver la conversación que lo definió. El backend
// (agents/orquestador.py::SesionTelos.confirmar_seleccion y hermanos) ya
// implementa exactamente esta mecánica; este componente es la traducción
// fiel de ese prototipo a React real, cableado a los endpoints
// verdaderos en vez de al estado local que usaba el mockup.
//
// Diferencia deliberada respecto al prototipo: acá el cierre ("Ver mi
// propósito") no abre un modal con un propósito calculado localmente --
// dispara el cierre real de Fase 1 (POST /api/seleccion/cerrar-fase1,
// que sintetiza con el modelo y guarda la ficha) y After arranca a Fase 2
// (el Sintetizador, vía onCerrado) para que presente los candidatos de
// verdad. El propósito final nunca lo inventa este componente.
//
// El chat de apoyo de acá es autocontenido con respuestas guiadas fijas
// (mismo criterio que el prototipo original) -- todavía NO habla con el
// backend real. Fase 1 ya no acepta texto libre como mecanismo principal
// (ver agents/orquestador.py, _PLACEHOLDER_FASE_1), así que conectar este
// chat al pipeline de conversación real necesita un endpoint de soporte
// dedicado que no se construyó en esta pasada -- pendiente, documentado
// acá a propósito para no perderlo de vista.

type Etapa = "l1" | "l2" | "l3" | "detail" | "values";

type NodoElegido = {
  id: string; // "verbo/dominio/hoja"
  verboId: string;
  verboLabel: string;
  dominioId: string;
  hojaLabel: string;
  desc: string;
  detalle: string;
  dims: string[];
};

const DIM_ANGULO: Record<string, number> = { L: -135, G: -45, V: 45, N: 135 };
const DIM_COLOR: Record<string, string> = { L: "#c8801f", G: "#4e4d86", V: "#a8532c", N: "#3a6d63" };
const INDIGO = "#4e4d86";
const ACENTO = "#a4552f";

const TEXTOS = {
  es: {
    tituloApp: "Telos",
    fraseInicial: "Descubramos qué te mueve.",
    subInicial: "No hay respuestas correctas. Cada elección nos ayudará a encontrar patrones únicos en ti.",
    comenzar: "Comenzar exploración",
    verComoFunciona: "Ver cómo funciona",
    soloElecciones: "Sin preguntas. Solo elecciones.",
    tuMapa: "Tu mapa",
    quitarDelMapa: "Quitar del mapa",
    volver: "← Volver",
    otraRama: "Otra rama",
    verProposito: "Ver mi propósito",
    detallePlaceholder: "¿algo más puntual dentro de esto?",
    agregarAlMapa: "Agregar al mapa",
    confirmarSinDetalle: "Confirmar sin detalle",
    trazarLimite: "Trazar el límite",
    limiteAyuda: "Esto no es otra área: envuelve todo lo demás. Elige hasta tres.",
    aunSinTocar: "aún sin trazar",
    tocaOtraArea: "toca otra área para cambiar",
    tocaUnArea: "toca un área del gráfico",
    completando: (label: string) => `Completando · ${label.toLowerCase()}`,
    nivel1: "Nivel 1 · amplio",
    nivel2: (v: string) => `${v} · nivel 2 · intermedio`,
    nivel3: (v: string, d: string) => `${v} → ${d} · nivel 3 · específico`,
    nivel4: "Nivel 4 · detalle libre",
    preguntaL1Focus: (label: string) => `Para nutrir "${label.toLowerCase()}", ¿por dónde entras?`,
    preguntaL1: "¿Dónde te atrae más explorar?",
    preguntaL2: (v: string) => `¿Hacia dónde, dentro de ${v.toLowerCase()}?`,
    preguntaL3: "Más preciso: ¿qué parte de esto es tuya?",
    preguntaDetalle: (hoja: string) => `¿Qué tipo de ${hoja.toLowerCase()}, específicamente?`,
    preguntaValores: "¿Qué no negociarías, pase lo que pase?",
    tocaCaminos: (n: number, label: string) => `${n} camino${n === 1 ? "" : "s"} hacia ${label.toLowerCase()}`,
    tocaDimensiones: (n: number) => `toca ${n} dimensiones`,
    ayudaChat: "¿Necesitas aclarar algo?",
    cerrarApoyo: "Cerrar apoyo",
    apoyoTitulo: "Apoyo",
    apoyoSub: "Pregunta lo que necesites aclarar",
    chatPlaceholder: "Escribe tu duda…",
    sugerencias: ["¿Qué significa esta categoría?", "No sé cuál me representa", "¿En qué se diferencian?"],
    mensajeInicialChat: "Estoy acá si algo no te queda claro. No hace falta escribir nada para avanzar: podés hacer toda la exploración eligiendo.",
    cerrandoFase: "Armando tu reflejo…",
    kickerVacio: "",
    kickerEspacio: "Espacio abierto",
    kickerSenal: "Señal",
    kickerPatron: "Patrón",
    kickerConvergencia: "Convergencia",
    subEspacio: "Elige por dónde empezar.",
    subSenal: "Estamos detectando un patrón…",
    subConvergencia: "Tu propósito comienza a tomar forma.",
    tour: [
      { zona: "El centro", titulo: "Tu mapa Ikigai", cuerpo: "El gráfico del medio es tu Ikigai: cuatro áreas de exploración y un anillo de valores que las envuelve. Empieza casi vacío y se define con cada elección." },
      { zona: "Abajo", titulo: "Elige para cada área", cuerpo: "Abajo aparecen pocas opciones por vez. Entras a una, bajas hasta lo más específico, confirmas y vuelves para explorar otra rama distinta." },
      { zona: "Arriba y en el gráfico", titulo: "Cada área se completa", cuerpo: "Verás el porcentaje de cada dimensión. Toca un área del gráfico y las opciones se reordenan para completar justo esa." },
      { zona: "Esquina", titulo: "Si dudas, pregunta", cuerpo: "El asistente es solo de apoyo: puedes recorrer toda la experiencia sin escribir una sola frase." },
    ],
    saltarGuia: "Saltar guía",
    atras: "Atrás",
    siguiente: "Siguiente",
    empezarDesdeGuia: "Comenzar exploración",
  },
  en: {
    tituloApp: "Telos",
    fraseInicial: "Let's find what moves you.",
    subInicial: "There are no right answers. Every choice helps us find patterns unique to you.",
    comenzar: "Start exploring",
    verComoFunciona: "See how it works",
    soloElecciones: "No questions. Just choices.",
    tuMapa: "Your map",
    quitarDelMapa: "Remove from map",
    volver: "← Back",
    otraRama: "Another branch",
    verProposito: "See my purpose",
    detallePlaceholder: "anything more specific about this?",
    agregarAlMapa: "Add to map",
    confirmarSinDetalle: "Confirm without detail",
    trazarLimite: "Draw the line",
    limiteAyuda: "This isn't another area: it wraps around everything else. Pick up to three.",
    aunSinTocar: "not drawn yet",
    tocaOtraArea: "tap another area to change",
    tocaUnArea: "tap an area of the chart",
    completando: (label: string) => `Filling in · ${label.toLowerCase()}`,
    nivel1: "Level 1 · broad",
    nivel2: (v: string) => `${v} · level 2 · mid`,
    nivel3: (v: string, d: string) => `${v} → ${d} · level 3 · specific`,
    nivel4: "Level 4 · free detail",
    preguntaL1Focus: (label: string) => `To feed "${label.toLowerCase()}", where do you enter?`,
    preguntaL1: "Where does exploring pull you most?",
    preguntaL2: (v: string) => `Toward where, within ${v.toLowerCase()}?`,
    preguntaL3: "More precise: which part of this is yours?",
    preguntaDetalle: (hoja: string) => `What kind of ${hoja.toLowerCase()}, specifically?`,
    preguntaValores: "What wouldn't you trade away, no matter what?",
    tocaCaminos: (n: number, label: string) => `${n} path${n === 1 ? "" : "s"} toward ${label.toLowerCase()}`,
    tocaDimensiones: (n: number) => `touches ${n} dimensions`,
    ayudaChat: "Need something clarified?",
    cerrarApoyo: "Close support",
    apoyoTitulo: "Support",
    apoyoSub: "Ask whatever you need clarified",
    chatPlaceholder: "Type your question…",
    sugerencias: ["What does this category mean?", "I don't know which fits me", "How are these different?"],
    mensajeInicialChat: "I'm here if anything's unclear. You don't need to type anything to move forward: you can do the whole exploration by choosing.",
    cerrandoFase: "Putting together your reflection…",
    kickerVacio: "",
    kickerEspacio: "Open space",
    kickerSenal: "Signal",
    kickerPatron: "Pattern",
    kickerConvergencia: "Convergence",
    subEspacio: "Choose where to start.",
    subSenal: "We're picking up a pattern…",
    subConvergencia: "Your purpose is starting to take shape.",
    tour: [
      { zona: "The center", titulo: "Your Ikigai map", cuerpo: "The chart in the middle is your Ikigai: four areas of exploration and a ring of values wrapping around them. It starts almost empty and takes shape with each choice." },
      { zona: "Below", titulo: "Choose for each area", cuerpo: "A few options show up at a time below. Go into one, drill down to something specific, confirm it, and come back to explore a different branch." },
      { zona: "Above and on the chart", titulo: "Each area fills in", cuerpo: "You'll see each dimension's percentage. Tap an area of the chart and the options reorder to fill in just that one." },
      { zona: "Corner", titulo: "If unsure, just ask", cuerpo: "The assistant is only for support: you can go through the whole experience without typing a single sentence." },
    ],
    saltarGuia: "Skip guide",
    atras: "Back",
    siguiente: "Next",
    empezarDesdeGuia: "Start exploring",
  },
} as const;

function unionDims(a: string, b: string): string[] {
  const vistas: string[] = [];
  for (const letra of a + b) if (!vistas.includes(letra)) vistas.push(letra);
  return vistas;
}

function polar(r: number, gradosAngulo: number): [number, number] {
  const t = (gradosAngulo * Math.PI) / 180;
  return [Math.cos(t) * r, Math.sin(t) * r];
}

function sectorPath(ri: number, ro: number, a0: number, a1: number): string {
  const [x0, y0] = polar(ro, a0);
  const [x1, y1] = polar(ro, a1);
  const [x2, y2] = polar(ri, a1);
  const [x3, y3] = polar(ri, a0);
  return `M${x0} ${y0} A${ro} ${ro} 0 0 1 ${x1} ${y1} L${x2} ${y2} A${ri} ${ri} 0 0 0 ${x3} ${y3} Z`;
}

function arcPath(r: number, a0: number, a1: number): string {
  const [x0, y0] = polar(r, a0);
  const [x1, y1] = polar(r, a1);
  return `M${x0} ${y0} A${r} ${r} 0 0 1 ${x1} ${y1}`;
}

export function ArbolSelector({
  idioma,
  nombre,
  onCerrado,
}: {
  idioma: Idioma;
  nombre: string | null;
  onCerrado: () => void;
}) {
  const t = TEXTOS[idioma];

  const [taxonomia, setTaxonomia] = useState<CategoriasFase1 | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [started, setStarted] = useState(false);
  const [stage, setStage] = useState<Etapa>("l1");
  const [path, setPath] = useState<string[]>([]);
  const [detalle, setDetalle] = useState("");
  const [focusDim, setFocusDim] = useState<string | null>(null);
  const [hoverOpt, setHoverOpt] = useState<string | null>(null);
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<{ who: "me" | "bot"; text: string }[]>([
    { who: "bot", text: t.mensajeInicialChat },
  ]);

  const [nodes, setNodes] = useState<NodoElegido[]>([]);
  const [cobertura, setCobertura] = useState<Record<string, number>>({ L: 0, G: 0, V: 0, N: 0 });
  const [valoresElegidos, setValoresElegidos] = useState<string[]>([]);
  const [puedeCerrar, setPuedeCerrar] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [cerrando, setCerrando] = useState(false);

  useEffect(() => {
    let cancelado = false;
    obtenerCategoriasFase1(idioma)
      .then((data) => {
        if (!cancelado) setTaxonomia(data);
      })
      .catch(() => {
        if (!cancelado) setError("No se pudo cargar el árbol de categorías. Recargá la página.");
      });
    return () => {
      cancelado = true;
    };
  }, [idioma]);

  const verbos: VerboIkigai[] = taxonomia?.verbos ?? [];
  const dominios = taxonomia?.dominios ?? {};
  const hojas = taxonomia?.hojas ?? {};

  const verboActivo = path[0] ? verbos.find((v) => v.id === path[0]) : undefined;
  const dominioActivoId = path[1];

  function domScore(dominioId: string, verbo: VerboIkigai, letraDim: string): number {
    const lista: HojaIkigai[] = hojas[dominioId] ?? [];
    return lista.filter((h) => unionDims(verbo.dims, h.dims).includes(letraDim)).length;
  }

  function rankeaItems<T extends { id: string; dims: string[] | string }>(items: T[]): (T & { atenuado?: boolean })[] {
    if (!focusDim) return items;
    const dimsDe = (it: T) => (Array.isArray(it.dims) ? it.dims : it.dims.split(""));
    const conMatch = items.filter((it) => dimsDe(it).includes(focusDim));
    if (conMatch.length >= 3) {
      const sinMatch = items.filter((it) => !dimsDe(it).includes(focusDim)).map((it) => ({ ...it, atenuado: true }));
      return [...conMatch, ...sinMatch];
    }
    return items;
  }

  const opciones = useMemo(() => {
    if (!taxonomia) return { pregunta: "", crumb: "", items: [] as { id: string; nombre: string; desc: string; dims: string[] }[] };

    if (stage === "l1") {
      const items = rankeaItems(verbos.map((v) => ({ id: v.id, nombre: v.label, desc: v.desc, dims: v.dims.split("") })));
      return {
        pregunta: focusDim ? t.preguntaL1Focus(t_etiqueta(focusDim)) : t.preguntaL1,
        crumb: focusDim ? t.completando(t_etiqueta(focusDim)) : t.nivel1,
        items,
      };
    }
    if (stage === "l2" && verboActivo) {
      const doms = focusDim
        ? [...verboActivo.dominios].sort((a, b) => domScore(b, verboActivo, focusDim) - domScore(a, verboActivo, focusDim))
        : verboActivo.dominios;
      const items = doms.map((d) => {
        const puntaje = focusDim ? domScore(d, verboActivo, focusDim) : 0;
        return {
          id: d,
          nombre: dominios[d]?.label ?? d,
          desc: focusDim && puntaje ? `${dominios[d]?.desc ?? ""} · ${t.tocaCaminos(puntaje, t_etiqueta(focusDim))}` : dominios[d]?.desc ?? "",
          dims: verboActivo.dims.split(""),
        };
      });
      return { pregunta: t.preguntaL2(verboActivo.label), crumb: t.nivel2(verboActivo.label), items };
    }
    if (stage === "l3" && verboActivo && dominioActivoId) {
      const lista = hojas[dominioActivoId] ?? [];
      const items = rankeaItems(
        lista.map((h) => ({ id: h.id, nombre: h.label, desc: h.desc, dims: unionDims(verboActivo.dims, h.dims) })),
      );
      return { pregunta: t.preguntaL3, crumb: t.nivel3(verboActivo.label, dominios[dominioActivoId]?.label ?? dominioActivoId), items };
    }
    return { pregunta: "", crumb: "", items: [] };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- taxonomia/focusDim/path ya cubren las dependencias reales
  }, [taxonomia, stage, path, focusDim]);

  function t_etiqueta(dim: string): string {
    return taxonomia?.etiquetasDimension[dim] ?? dim;
  }

  function focalizar(dim: string) {
    setFocusDim((actual) => (actual === dim ? null : dim));
    setStarted(true);
    setStage((s) => (s === "values" ? "values" : "l1"));
    setPath([]);
    setDetalle("");
  }

  function elegir(id: string) {
    if (stage === "l1") {
      setPath([id]);
      setStage("l2");
    } else if (stage === "l2" && path[0]) {
      setPath([path[0], id]);
      setStage("l3");
    } else if (stage === "l3" && path[0] && path[1]) {
      setPath([path[0], path[1], id]);
      setStage("detail");
    }
  }

  async function confirmar(conDetalle: boolean) {
    if (!verboActivo || !dominioActivoId || !path[2]) return;
    const hoja = (hojas[dominioActivoId] ?? []).find((h) => h.id === path[2]);
    if (!hoja) return;
    const dims = unionDims(verboActivo.dims, hoja.dims);
    const detalleTexto = conDetalle ? detalle.trim() : "";
    const nodoId = `${verboActivo.id}/${dominioActivoId}/${hoja.id}`;

    const nuevoNodo: NodoElegido = {
      id: nodoId,
      verboId: verboActivo.id,
      verboLabel: verboActivo.label,
      dominioId: dominioActivoId,
      hojaLabel: hoja.label,
      desc: hoja.desc,
      detalle: detalleTexto,
      dims,
    };

    setGuardando(true);
    setError(null);
    try {
      const resultado = await confirmarSeleccion({
        fase: 1,
        nodoId,
        idioma,
        detalleLibre: detalleTexto || undefined,
      });
      setNodes((prev) => [...prev.filter((n) => n.id !== nodoId), nuevoNodo]);
      setCobertura(resultado.cobertura ?? {});
      setPuedeCerrar(resultado.puede_cerrar);
      const vaAValores = resultado.mostrar_valores;
      const dimCubierta = focusDim && dims.includes(focusDim) ? null : focusDim;
      setPath([]);
      setDetalle("");
      setStage(vaAValores ? "values" : "l1");
      setFocusDim(dimCubierta);
    } catch {
      setError(idioma === "es" ? "No se pudo guardar la elección. Probá de nuevo." : "Couldn't save that choice. Try again.");
    } finally {
      setGuardando(false);
    }
  }

  async function confirmarPasoValores() {
    setGuardando(true);
    setError(null);
    try {
      await confirmarValores(valoresElegidos, idioma);
      setStage("l1");
    } catch {
      setError(idioma === "es" ? "No se pudieron guardar los valores. Probá de nuevo." : "Couldn't save your values. Try again.");
    } finally {
      setGuardando(false);
    }
  }

  async function verMiProposito() {
    setCerrando(true);
    setError(null);
    try {
      await cerrarFase1(idioma);
      onCerrado();
    } catch {
      setError(idioma === "es" ? "No se pudo cerrar esta fase. Probá de nuevo." : "Couldn't close this phase. Try again.");
      setCerrando(false);
    }
  }

  function volver() {
    if (path.length === 3) {
      setPath(path.slice(0, 2));
      setStage("l3");
    } else if (path.length === 2) {
      setPath(path.slice(0, 1));
      setStage("l2");
    } else {
      setPath([]);
      setStage("l1");
    }
  }

  function enviarChat(texto: string) {
    const limpio = texto.trim();
    if (!limpio) return;
    const bajo = limpio.toLowerCase();
    let respuesta =
      idioma === "es"
        ? "Buena duda. Elige la opción que te resulte más viva hoy: nada queda fijo, puedes quitarla del mapa después y el gráfico se recalcula."
        : "Good question. Pick whichever option feels most alive today: nothing is fixed, you can remove it from the map later and the chart recalculates.";
    if (bajo.includes("signif") || bajo.includes("mean")) {
      respuesta =
        idioma === "es"
          ? "Cada tarjeta es una zona de actividad, no una respuesta. Si te cuesta imaginarte ahí dentro, probablemente no sea tuya."
          : "Each card is a zone of activity, not an answer. If you can't picture yourself in it, it's probably not yours.";
    } else if (bajo.includes("difer") || bajo.includes("differ")) {
      respuesta =
        idioma === "es"
          ? "La diferencia está en qué dimensiones ilumina cada una: fíjate en la línea inferior de la tarjeta. Las que tocan tres pesan más en el centro."
          : "The difference is which dimensions each one lights up: check the bottom line of the card. Ones touching three weigh more in the center.";
    } else if (bajo.includes("no s") || bajo.includes("segur") || bajo.includes("sure") || bajo.includes("don't know")) {
      respuesta =
        idioma === "es"
          ? "Puedes entrar a una rama solo para ver qué hay más adentro y volver con \"Otra rama\". Explorar no compromete nada."
          : "You can go into a branch just to see what's inside and come back with \"Another branch\". Exploring doesn't commit you to anything.";
    } else if (bajo.includes("valor") || bajo.includes("value")) {
      respuesta =
        idioma === "es"
          ? "Tus valores no son un área más: son el borde. Filtran todo lo que elijas, por eso aparecen como el anillo que envuelve el mapa."
          : "Your values aren't one more area: they're the edge. They filter everything you choose, that's why they show up as the ring around the map.";
    }
    setMessages((prev) => [...prev, { who: "me", text: limpio }, { who: "bot", text: respuesta }]);
    setDraft("");
  }

  // ---------- visualización ----------

  const conteos = { L: cobertura.L ?? 0, G: cobertura.G ?? 0, V: cobertura.V ?? 0, N: cobertura.N ?? 0 };
  const dimensiones = (taxonomia?.dimensiones ?? ["L", "G", "V", "N"]) as string[];

  const nodosPosicionados = useMemo(() => {
    return nodes.map((n, i) => {
      let x = 0;
      let y = 0;
      n.dims.forEach((k) => {
        const a = (DIM_ANGULO[k] * Math.PI) / 180;
        x += Math.cos(a);
        y += Math.sin(a);
      });
      let ang = Math.atan2(y, x);
      ang += ((i % 3) - 1) * 0.3;
      const w = n.dims.length;
      const ca = Math.abs(Math.cos(ang));
      const sa = Math.abs(Math.sin(ang));
      const clear = Math.min(232, Math.max(148 / Math.max(ca, 0.001), 126 / Math.max(sa, 0.001)));
      const r = Math.min(232, Math.max(clear + 14, 210 - w * 10 + (i % 2) * 10));
      return { n, w, x: Math.cos(ang) * r, y: Math.sin(ang) * r };
    });
  }, [nodes]);

  function construirGrafico() {
    const elementos: React.ReactNode[] = [];
    [230, 176, 120, 66].forEach((r, i) =>
      elementos.push(<circle key={`f${i}`} r={r} fill="none" stroke="#1b1917" strokeWidth={0.5} opacity={0.09} />),
    );

    dimensiones.forEach((d) => {
      const angulo = DIM_ANGULO[d];
      const color = DIM_COLOR[d];
      const cov = Math.min(1, conteos[d as keyof typeof conteos] / 3);
      const a0 = angulo - 43;
      const a1 = angulo + 43;
      const listo = cov >= 1;
      const enfocado = focusDim === d;
      if (enfocado) {
        elementos.push(
          <path key={`fc${d}`} d={sectorPath(46, 238, a0 - 2, a1 + 2)} fill="none" stroke={color} strokeWidth={1.2} opacity={0.5} strokeDasharray="6 6" />,
        );
      }
      elementos.push(<path key={`sec${d}`} d={sectorPath(48, 96 + cov * 122, a0, a1)} fill={color} opacity={0.035 + cov * 0.17} style={{ transition: "opacity .9s ease" }} />);
      if (cov > 0) elementos.push(<path key={`seci${d}`} d={sectorPath(48, 96 + cov * 60, a0 + 10, a1 - 10)} fill={color} opacity={0.05 + cov * 0.12} />);
      elementos.push(
        <path key={`arcb${d}`} d={arcPath(226, a0, a1)} fill="none" stroke={color} strokeWidth={1} opacity={0.12} strokeLinecap="round" />,
      );
      elementos.push(
        <path
          key={`arcf${d}`}
          d={arcPath(226, a0, a0 + (a1 - a0) * cov)}
          fill="none"
          stroke={color}
          strokeWidth={listo ? 3 : 1.9}
          opacity={listo ? 0.95 : 0.55}
          strokeLinecap="round"
          style={{ transition: "all .9s cubic-bezier(.22,.9,.25,1)" }}
        />,
      );
      if (listo) {
        const [dx, dy] = polar(226, angulo);
        elementos.push(<circle key={`arcd${d}`} cx={dx} cy={dy} r={5.5} fill={color} opacity={0.2} />);
      }
      const [px, py] = polar(126 + cov * 54, angulo);
      elementos.push(
        <text
          key={`pct${d}`}
          x={px}
          y={py + 4}
          textAnchor="middle"
          fill={color}
          opacity={listo ? 0.9 : 0.62}
          fontSize={listo ? 12 : 11}
          fontFamily="var(--font-ibm-plex-mono), monospace"
          letterSpacing={1.2}
          pointerEvents="none"
        >
          {Math.round(cov * 100)}%
        </text>,
      );
      elementos.push(
        <path
          key={`hit${d}`}
          d={sectorPath(46, 240, a0, a1)}
          fill="#fff"
          opacity={0}
          onClick={() => focalizar(d)}
          style={{ cursor: "pointer" }}
        />,
      );
    });

    const vc = valoresElegidos.length;
    elementos.push(
      <circle
        key="ring"
        r={246}
        fill="none"
        stroke={vc ? INDIGO : "#1b1917"}
        strokeWidth={vc ? 1.2 : 0.7}
        opacity={vc ? 0.24 + vc * 0.14 : 0.14}
        strokeDasharray={vc >= 3 ? "none" : vc ? "26 9" : "2 11"}
      />,
    );
    if (vc)
      dimensiones.forEach((d) => {
        const a = ((DIM_ANGULO[d] + 45) * Math.PI) / 180;
        elementos.push(
          <line key={`vr${d}`} x1={Math.cos(a) * 60} y1={Math.sin(a) * 60} x2={Math.cos(a) * 246} y2={Math.sin(a) * 246} stroke={INDIGO} strokeWidth={0.6} opacity={0.2} />,
        );
      });
    valoresElegidos.slice(0, 3).forEach((v, i) => {
      const a = ((-90 + i * 120) * Math.PI) / 180;
      elementos.push(
        <text key={`vt${i}`} x={Math.cos(a) * 246} y={Math.sin(a) * 246 + 4} textAnchor="middle" fill={INDIGO} fontSize={11} fontFamily="var(--font-ibm-plex-mono), monospace" letterSpacing={1.4} opacity={0.9}>
          {v.toUpperCase()}
        </text>,
      );
    });

    dimensiones.forEach((d) => {
      const angulo = DIM_ANGULO[d];
      const [ax, ay] = polar(150, angulo);
      const cov = Math.min(1, conteos[d as keyof typeof conteos] / 3);
      const color = DIM_COLOR[d];
      elementos.push(<circle key={`dg${d}`} cx={ax} cy={ay} r={40 + cov * 26} fill={color} opacity={0.05 + cov * 0.14} />);
      elementos.push(<circle key={`dg2${d}`} cx={ax} cy={ay} r={(40 + cov * 26) * 0.58} fill={color} opacity={0.04 + cov * 0.12} />);
      elementos.push(<circle key={`dd${d}`} cx={ax} cy={ay} r={3.4} fill={cov ? color : "#c3bab0"} opacity={cov ? 1 : 0.6} />);
      const [lx, ly] = polar(252, angulo);
      elementos.push(
        <text key={`dl${d}`} x={lx} y={ly + (ay < 0 ? -8 : 16)} textAnchor="middle" fill={cov ? color : "#a8a096"} fontSize={11.5} fontFamily="var(--font-ibm-plex-mono), monospace" letterSpacing={1.6}>
          {t_etiqueta(d).toUpperCase()}
        </text>,
      );
    });

    nodosPosicionados.forEach((p, i) => {
      p.n.dims.forEach((k, j) => {
        const a = (DIM_ANGULO[k] * Math.PI) / 180;
        const color = DIM_COLOR[k];
        elementos.push(
          <line key={`ln${i}-${j}`} x1={p.x} y1={p.y} x2={Math.cos(a) * 150} y2={Math.sin(a) * 150} stroke={color} strokeWidth={0.9} opacity={0.18 + p.w * 0.07} strokeLinecap="round" />,
        );
        elementos.push(<line key={`lc${i}-${j}`} x1={p.x} y1={p.y} x2={0} y2={0} stroke="#1b1917" strokeWidth={0.5} opacity={0.07} />);
      });
    });

    nodosPosicionados.forEach((p, i) => {
      const nc = p.w >= 3 ? ACENTO : DIM_COLOR[p.n.dims[0]] ?? ACENTO;
      elementos.push(<circle key={`nh${i}`} cx={p.x} cy={p.y} r={8 + p.w * 4} fill={nc} opacity={0.14} />);
      elementos.push(<circle key={`nd${i}`} cx={p.x} cy={p.y} r={3 + p.w * 1.5} fill={nc} opacity={0.95} style={{ animation: "telos-fade .9s ease both" }} />);
      elementos.push(
        <text key={`nl${i}`} x={p.x} y={p.y - (10 + p.w * 4)} textAnchor="middle" fill="#2c2823" fontSize={p.w >= 3 ? 13 : 12} fontFamily="var(--font-instrument-sans), sans-serif" opacity={p.w >= 3 ? 0.95 : 0.7}>
          {p.n.hojaLabel}
        </text>,
      );
    });

    const conv = dimensiones.reduce((acc, d) => acc + Math.min(1, conteos[d as keyof typeof conteos] / 3), 0) / dimensiones.length;
    elementos.push(<circle key="c0" r={74} fill={ACENTO} opacity={0.02 + conv * 0.06} />);
    elementos.push(<circle key="c1" r={52} fill={ACENTO} opacity={0.04 + conv * 0.22} style={{ transition: "opacity 1s ease" }} />);
    elementos.push(
      <circle
        key="c2"
        r={58 * (0.45 + conv * 0.55)}
        fill="none"
        stroke={ACENTO}
        strokeWidth={conv > 0.7 ? 1.4 : 0.7}
        opacity={0.18 + conv * 0.5}
        strokeDasharray={conv >= 1 ? "none" : "18 8"}
        style={{ animation: "telos-breathe 6s ease-in-out infinite", transition: "all .9s ease" }}
      />,
    );
    if (conv >= 1) elementos.push(<circle key="c3" r={26} fill={ACENTO} opacity={0.3} />);

    return (
      <svg viewBox="-270 -270 540 540" width="100%" height="100%" preserveAspectRatio="xMidYMid meet" style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        {elementos}
      </svg>
    );
  }

  // ---------- centro ----------
  const nodeCount = nodes.length;
  let centerKicker: string = t.kickerVacio;
  let centerTitle: string = t.fraseInicial;
  let centerSub: string = t.subInicial;
  if (started) {
    if (nodeCount === 0) {
      centerKicker = t.kickerEspacio;
      centerTitle = t.subEspacio;
      centerSub = "";
    } else if (nodeCount === 1) {
      centerKicker = t.kickerSenal;
      centerTitle = t.subSenal;
      centerSub = "";
    } else if (nodeCount === 2) {
      centerKicker = t.kickerPatron;
      centerTitle =
        idioma === "es"
          ? `Conexión entre ${nodes[0].hojaLabel.toLowerCase()} y ${nodes[1].hojaLabel.toLowerCase()}.`
          : `A connection between ${nodes[0].hojaLabel.toLowerCase()} and ${nodes[1].hojaLabel.toLowerCase()}.`;
      centerSub = "";
    } else if (nodeCount === 3) {
      centerKicker = t.kickerConvergencia;
      centerTitle = t.subConvergencia;
      centerSub = "";
    } else {
      centerKicker = idioma === "es" ? "Tu patrón" : "Your pattern";
      centerTitle = idioma === "es" ? "Tenés suficiente material para reflejar algo real." : "You have enough material to reflect something real.";
      centerSub = "";
    }
  }

  const canSeeResult = puedeCerrar && stage === "l1";
  const tourActual = t.tour[tourStep ?? 0];

  if (error && !taxonomia) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-foreground/70">{error}</div>
    );
  }

  if (!taxonomia) {
    return <div className="flex flex-1 items-center justify-center p-8 text-sm text-foreground/50">…</div>;
  }

  return (
    <div
      className="telos-arbol-selector"
      style={{
        height: "100%",
        minHeight: 0,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        background:
          "radial-gradient(80% 55% at 50% 62%, rgba(226,164,74,.20) 0%, rgba(226,164,74,0) 62%), radial-gradient(70% 60% at 8% 4%, rgba(78,77,134,.16) 0%, rgba(78,77,134,0) 70%), radial-gradient(70% 60% at 95% 6%, rgba(58,109,99,.12) 0%, rgba(58,109,99,0) 70%), linear-gradient(#fcfaf7 0%, #f5f1ea 60%, #efe8dd 100%)",
        fontFamily: "var(--font-instrument-sans), system-ui, sans-serif",
        color: "#1b1917",
        position: "relative",
      }}
    >
      <style>{`
        @keyframes telos-rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
        @keyframes telos-fade { from { opacity:0; } to { opacity:1; } }
        @keyframes telos-breathe { 0%,100% { opacity:.55; transform:scale(1); } 50% { opacity:.85; transform:scale(1.035); } }

        /* Mobile: la versión desktop (un solo viewport sin scroll,
           gráfico grande, grid de auto-fill) no deja lugar para todo en
           una pantalla angosta -- se prioriza que nada quede cortado por
           sobre la estética de "todo cabe en una vista", mismo criterio
           que el resto del proyecto ("que funcione" antes que pixel
           perfect en el MVP). */
        @media (max-width: 640px) {
          .telos-arbol-selector { overflow-y: auto !important; height: auto !important; min-height: 100%; }
          .telos-grafico { height: min(72vw, 340px) !important; }
          .telos-opciones-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
        }
        @media (max-width: 380px) {
          .telos-opciones-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, padding: "12px clamp(18px,4vw,46px) 6px", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 13, letterSpacing: ".34em", textTransform: "uppercase" }}>{t.tituloApp}</div>
          {nombre && <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".14em", textTransform: "uppercase", color: "#9c948a" }}>{nombre}</div>}
        </div>

        <div style={{ display: "flex", gap: "clamp(10px,2vw,26px)", flexWrap: "wrap", alignItems: "flex-start" }}>
          {dimensiones.map((d) => {
            const cov = Math.min(1, conteos[d as keyof typeof conteos] / 3);
            const labelColor = cov >= 1 ? DIM_COLOR[d] : cov > 0 ? "#6b6459" : "#a8a096";
            return (
              <button
                key={d}
                onClick={() => focalizar(d)}
                style={{
                  textAlign: "left",
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                  minWidth: 104,
                  background: "transparent",
                  border: "none",
                  borderBottom: `1px solid ${focusDim === d ? DIM_COLOR[d] : "transparent"}`,
                  padding: "2px 0 4px",
                  cursor: "pointer",
                  transition: "all .3s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "baseline", gap: 7, fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".15em", textTransform: "uppercase" }}>
                  <span style={{ color: labelColor }}>{t_etiqueta(d)}</span>
                  <span style={{ color: "#b0a79a", fontSize: 8.5 }}>{Math.round(cov * 100)}%</span>
                </div>
                <div style={{ height: 2, width: "100%", background: "#ded7cc", position: "relative", overflow: "hidden" }}>
                  <div style={{ position: "absolute", inset: "0 auto 0 0", background: DIM_COLOR[d], transition: "width .7s cubic-bezier(.22,.9,.25,1)", width: `${Math.round(cov * 100)}%` }} />
                </div>
              </button>
            );
          })}
          <div style={{ display: "flex", alignItems: "baseline", gap: 7, fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".15em", textTransform: "uppercase" }}>
            <span style={{ color: "#8c8478" }}>{idioma === "es" ? "Tus valores" : "Your values"}</span>
            <span style={{ color: "#5d564d", letterSpacing: ".06em", textTransform: "none" }}>{valoresElegidos.length ? valoresElegidos.join(" · ") : t.aunSinTocar}</span>
          </div>
        </div>
      </header>

      {nodeCount > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: "2px clamp(18px,4vw,46px) 0", alignItems: "center" }}>
          <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".15em", textTransform: "uppercase", color: "#9c948a", marginRight: 2 }}>{t.tuMapa}</span>
          {nodes.map((n) => (
            <button
              key={n.id}
              title={t.quitarDelMapa}
              onClick={() => setNodes((prev) => prev.filter((x) => x.id !== n.id))}
              style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid #ded7cc", background: "#fbf9f6", borderRadius: 999, padding: "5px 11px 5px 9px", cursor: "pointer", color: "#3b3630", fontSize: 12.5, animation: "telos-fade .5s ease both" }}
            >
              <span style={{ width: 7, height: 7, borderRadius: 999, background: n.dims.length >= 3 ? ACENTO : DIM_COLOR[n.dims[0]], opacity: 0.45 + n.dims.length * 0.14 }} />
              <span>
                {n.hojaLabel}
                {n.detalle ? ` · ${n.detalle}` : ""}
              </span>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, color: "#a09689" }}>×{n.dims.length}</span>
            </button>
          ))}
        </div>
      )}

      <main style={{ flex: "1 1 auto", minHeight: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: "clamp(10px,2vw,34px)", position: "relative", padding: "4px 12px" }}>
        <div className="telos-grafico" style={{ position: "relative", height: "min(100%, 58vw, 560px)", aspectRatio: "1/1", flex: "none", display: "flex", alignItems: "center", justifyContent: "center" }}>
          {construirGrafico()}
          <div style={{ position: "absolute", left: "24%", top: "29%", width: "52%", height: "42%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", gap: 6, pointerEvents: "none", overflow: "hidden" }}>
            <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9, letterSpacing: ".2em", textTransform: "uppercase", color: ACENTO }}>{centerKicker}</div>
            <div style={{ fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(16px,2vw,27px)", lineHeight: 1.1 }}>{centerTitle}</div>
            <div style={{ fontSize: 11.5, lineHeight: 1.35, color: "#6b6459" }}>{centerSub}</div>
          </div>
        </div>
      </main>

      {!started && (
        <section style={{ flex: "none", display: "flex", flexDirection: "column", alignItems: "center", gap: 13, padding: "0 24px clamp(14px,2.5vh,40px)", animation: "telos-rise .8s ease both" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
            <button
              onClick={() => setStarted(true)}
              style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "14px 30px", fontSize: 14.5, cursor: "pointer" }}
            >
              {t.comenzar}
            </button>
            <button
              onClick={() => setTourStep(0)}
              style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "14px 22px", fontSize: 13.5, cursor: "pointer" }}
            >
              {t.verComoFunciona}
            </button>
          </div>
          <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 10, letterSpacing: ".14em", textTransform: "uppercase", color: "#a8a096" }}>{t.soloElecciones}</div>
        </section>
      )}

      {started && (
        <section style={{ flex: "none", padding: "0 clamp(16px,4vw,46px) 4px", animation: "telos-rise .6s ease both" }}>
          <div style={{ maxWidth: 1120, margin: "0 auto", display: "flex", flexDirection: "column", gap: 9 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9, flexWrap: "wrap" }}>
                  <div style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".16em", textTransform: "uppercase", color: ACENTO }}>
                    {stage === "values" ? (idioma === "es" ? "El límite que atraviesa todo" : "The line that runs through everything") : stage === "detail" ? t.nivel4 : opciones.crumb}
                  </div>
                  {focusDim && (
                    <button
                      onClick={() => setFocusDim(null)}
                      style={{ display: "flex", alignItems: "center", gap: 8, border: `1px solid ${DIM_COLOR[focusDim]}`, background: "transparent", borderRadius: 999, padding: "3px 10px", cursor: "pointer", fontSize: 11.5, color: "#3b3630" }}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: 999, background: DIM_COLOR[focusDim] }} />
                      <span>
                        {t_etiqueta(focusDim)} · {Math.round(Math.min(1, conteos[focusDim as keyof typeof conteos] / 3) * 100)}%
                      </span>
                      <span style={{ color: "#a09689" }}>×</span>
                    </button>
                  )}
                  {stage !== "values" && stage !== "detail" && <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9, letterSpacing: ".14em", textTransform: "uppercase", color: "#b0a79a" }}>{focusDim ? t.tocaOtraArea : t.tocaUnArea}</span>}
                </div>
                <h2 style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontSize: "clamp(17px,1.9vw,23px)", fontWeight: 400 }}>
                  {stage === "values" ? t.preguntaValores : stage === "detail" ? t.preguntaDetalle(path[2] ?? "") : opciones.pregunta}
                </h2>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={() => setChatOpen((v) => !v)}
                  style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "8px 16px", fontSize: 12.5, cursor: "pointer" }}
                >
                  <span style={{ width: 7, height: 7, borderRadius: 999, background: "#c8801f", animation: "telos-breathe 3.4s ease-in-out infinite" }} />
                  <span>{chatOpen ? t.cerrarApoyo : t.ayudaChat}</span>
                </button>
                {path.length > 0 && stage !== "values" && (
                  <button onClick={volver} style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "8px 16px", fontSize: 12.5, cursor: "pointer" }}>
                    {t.volver}
                  </button>
                )}
                {(path.length > 0 || stage === "detail") && stage !== "values" && (
                  <button
                    onClick={() => {
                      setPath([]);
                      setStage("l1");
                      setDetalle("");
                    }}
                    style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "8px 16px", fontSize: 12.5, cursor: "pointer" }}
                  >
                    {t.otraRama}
                  </button>
                )}
                {canSeeResult && (
                  <button
                    onClick={verMiProposito}
                    disabled={cerrando}
                    style={{ border: `1px solid ${ACENTO}`, background: ACENTO, color: "#fbf9f6", borderRadius: 999, padding: "8px 18px", fontSize: 12.5, cursor: "pointer", opacity: cerrando ? 0.6 : 1 }}
                  >
                    {cerrando ? t.cerrandoFase : t.verProposito}
                  </button>
                )}
              </div>
            </div>

            {stage === "detail" && (
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", border: "1px solid #e2dbd0", background: "#fbf9f6", borderRadius: 16, padding: "16px 18px" }}>
                <input
                  value={detalle}
                  onChange={(e) => setDetalle(e.target.value)}
                  placeholder={t.detallePlaceholder}
                  style={{ flex: 1, minWidth: 220, border: "none", background: "transparent", outline: "none", fontSize: 15, color: "#1b1917" }}
                />
                <button
                  onClick={() => confirmar(true)}
                  disabled={guardando}
                  style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "10px 20px", fontSize: 13, cursor: "pointer", opacity: guardando ? 0.6 : 1 }}
                >
                  {t.agregarAlMapa}
                </button>
                <button onClick={() => confirmar(false)} disabled={guardando} style={{ border: "none", background: "transparent", color: "#8c8478", fontSize: 12.5, cursor: "pointer", textDecoration: "underline" }}>
                  {t.confirmarSinDetalle}
                </button>
              </div>
            )}

            {stage === "values" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ display: "flex", gap: 9, flexWrap: "wrap" }}>
                  {taxonomia.valoresDisponibles.map((v) => {
                    const on = valoresElegidos.includes(v);
                    return (
                      <button
                        key={v}
                        onClick={() =>
                          setValoresElegidos((prev) =>
                            on ? prev.filter((x) => x !== v) : prev.length >= taxonomia.maxValores ? prev : [...prev, v],
                          )
                        }
                        style={{
                          border: `1px solid ${on ? ACENTO : "#e2dbd0"}`,
                          background: on ? "rgba(164,85,47,.08)" : "transparent",
                          color: on ? "#1b1917" : "#6b6459",
                          borderRadius: 999,
                          padding: "10px 18px",
                          fontSize: 13.5,
                          cursor: "pointer",
                          transition: "all .28s ease",
                        }}
                      >
                        {v}
                      </button>
                    );
                  })}
                </div>
                <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                  <button
                    onClick={confirmarPasoValores}
                    disabled={guardando}
                    style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "10px 22px", fontSize: 13, cursor: "pointer", opacity: guardando ? 0.6 : 1 }}
                  >
                    {t.trazarLimite}
                  </button>
                  <span style={{ fontSize: 12.5, color: "#8c8478" }}>{t.limiteAyuda}</span>
                </div>
              </div>
            )}

            {(stage === "l1" || stage === "l2" || stage === "l3") && (
              <div className="telos-opciones-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: "clamp(6px,.8vw,11px)", minWidth: 0 }}>
                {opciones.items.map((it, i) => (
                  <button
                    key={it.id}
                    onClick={() => elegir(it.id)}
                    onMouseEnter={() => setHoverOpt(it.id)}
                    onMouseLeave={() => setHoverOpt(null)}
                    style={{
                      position: "relative",
                      textAlign: "left",
                      display: "flex",
                      flexDirection: "column",
                      gap: 7,
                      border: "1px solid #e6ddd0",
                      background: it.dims.length >= 3 ? "linear-gradient(160deg, rgba(200,128,31,.10), rgba(251,249,246,1) 58%)" : "#fbf9f6",
                      borderRadius: 14,
                      padding: "13px 14px 15px",
                      cursor: "pointer",
                      animation: "telos-rise .5s ease both",
                      animationDelay: `${i * 45}ms`,
                    }}
                  >
                    <span style={{ fontSize: 14.5, lineHeight: 1.2, color: "#1b1917" }}>{it.nombre}</span>
                    {hoverOpt === it.id && (
                      <span
                        style={{
                          position: "absolute",
                          left: 0,
                          right: 0,
                          bottom: "calc(100% + 6px)",
                          background: "#fbf9f6",
                          border: "1px solid #e6ddd0",
                          borderRadius: 11,
                          padding: "8px 10px",
                          fontSize: 12,
                          lineHeight: 1.4,
                          color: "#5d564d",
                          boxShadow: "0 14px 30px -22px rgba(27,25,23,.6)",
                          zIndex: 1,
                        }}
                      >
                        {it.desc}
                      </span>
                    )}
                    <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9, letterSpacing: ".14em", textTransform: "uppercase", color: "#b0a79a" }}>
                      {it.dims.length >= 3 ? t.tocaDimensiones(it.dims.length) : it.dims.map((k) => t_etiqueta(k).toLowerCase()).join(" · ")}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {error && <div style={{ padding: "0 clamp(18px,4vw,46px) 10px", fontSize: 12.5, color: "#a4552f" }}>{error}</div>}

      {tourStep !== null && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(28,25,22,.3)", backdropFilter: "blur(5px)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24, zIndex: 60 }}>
          <div style={{ width: "100%", maxWidth: 470, background: "#fbf9f6", border: "1px solid #e2dbd0", borderRadius: 20, padding: "26px 26px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".2em", textTransform: "uppercase" }}>
              <span style={{ color: "#c8801f" }}>{tourActual.zona}</span>
              <span style={{ color: "#b0a79a" }}>
                {(tourStep ?? 0) + 1} / {t.tour.length}
              </span>
            </div>
            <h3 style={{ margin: 0, fontFamily: "var(--font-instrument-serif), Georgia, serif", fontWeight: 400, fontSize: "clamp(22px,2.6vw,30px)", lineHeight: 1.14 }}>{tourActual.titulo}</h3>
            <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.55, color: "#5d564d" }}>{tourActual.cuerpo}</p>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
              <button onClick={() => setTourStep(null)} style={{ border: "none", background: "transparent", color: "#8c8478", fontSize: 12.5, cursor: "pointer", textDecoration: "underline" }}>
                {t.saltarGuia}
              </button>
              <div style={{ display: "flex", gap: 8 }}>
                {(tourStep ?? 0) > 0 && (
                  <button onClick={() => setTourStep((s) => Math.max(0, (s ?? 0) - 1))} style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", borderRadius: 999, padding: "10px 18px", fontSize: 13, cursor: "pointer" }}>
                    {t.atras}
                  </button>
                )}
                {(tourStep ?? 0) === t.tour.length - 1 ? (
                  <button
                    onClick={() => {
                      setTourStep(null);
                      setStarted(true);
                    }}
                    style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "10px 22px", fontSize: 13, cursor: "pointer" }}
                  >
                    {t.empezarDesdeGuia}
                  </button>
                ) : (
                  <button onClick={() => setTourStep((s) => Math.min(t.tour.length - 1, (s ?? 0) + 1))} style={{ border: "1px solid #1b1917", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, padding: "10px 22px", fontSize: 13, cursor: "pointer" }}>
                    {t.siguiente}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {started && !chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          style={{
            position: "fixed",
            right: "clamp(14px,2.4vw,28px)",
            bottom: "clamp(14px,2.4vw,28px)",
            zIndex: 30,
            display: "flex",
            alignItems: "center",
            gap: 10,
            border: "1px solid #ded7cc",
            background: "rgba(251,249,246,.92)",
            backdropFilter: "blur(8px)",
            color: "#3b3630",
            borderRadius: 999,
            padding: "11px 18px",
            fontSize: 13,
            cursor: "pointer",
            boxShadow: "0 14px 34px -22px rgba(27,25,23,.6)",
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: 999, background: "#c8801f", boxShadow: "0 0 0 4px rgba(200,128,31,.18)", animation: "telos-breathe 3.4s ease-in-out infinite" }} />
          <span>{t.ayudaChat}</span>
        </button>
      )}

      {chatOpen && (
        <aside style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(384px,100%)", zIndex: 50, background: "#fbf9f6", borderLeft: "1px solid #e2dbd0", display: "flex", flexDirection: "column", boxShadow: "-30px 0 60px -50px rgba(27,25,23,.7)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px", borderBottom: "1px solid #ece6dc" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <span style={{ fontFamily: "var(--font-ibm-plex-mono), monospace", fontSize: 9.5, letterSpacing: ".18em", textTransform: "uppercase", color: ACENTO }}>{t.apoyoTitulo}</span>
              <span style={{ fontSize: 14.5 }}>{t.apoyoSub}</span>
            </div>
            <button onClick={() => setChatOpen(false)} style={{ border: "1px solid #ded7cc", background: "transparent", color: "#5d564d", width: 30, height: 30, borderRadius: 999, cursor: "pointer", fontSize: 14, lineHeight: 1 }}>
              ×
            </button>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "18px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
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
          <div style={{ padding: "12px 20px 16px", borderTop: "1px solid #ece6dc", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              {t.sugerencias.map((s) => (
                <button
                  key={s}
                  onClick={() => enviarChat(s)}
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
                  if (e.key === "Enter") enviarChat(draft);
                }}
                placeholder={t.chatPlaceholder}
                style={{ flex: 1, border: "none", background: "transparent", outline: "none", fontSize: 13.5, color: "#1b1917" }}
              />
              <button onClick={() => enviarChat(draft)} style={{ border: "none", background: "#1b1917", color: "#f7f4ef", borderRadius: 999, width: 32, height: 32, cursor: "pointer", fontSize: 13 }}>
                →
              </button>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
