# Lineamientos de desarrollo — Telos

Este documento define cómo desarrollamos (no qué construimos — eso sigue
siendo `docs/agente-proposito-de-vida-prompts.md`). Nace de revisar cuatro
fuentes externas y de contrastarlas contra el código que ya existe en este
repo, no de aplicarlas al pie de la letra. Se va a usar como checklist en
una revisión de código próxima: cada punto está escrito para ser
verificable, no como aspiración.

## 0. Fuentes y qué nos llevamos de cada una

| Fuente | Qué es | Qué nos llevamos |
|---|---|---|
| [awslabs/agentcore-samples](https://github.com/awslabs/agentcore-samples) | Ejemplos oficiales de AWS para Runtime, Gateway, Memory, Identity, Observability de Bedrock AgentCore | Convenciones de cómo estructurar la integración con AgentCore (secciones 3-4) |
| [strands-agents](https://github.com/strands-agents) (`sdk-python`, `tools`, `samples`) | El SDK que ya usamos en `agents/`+`tools/` | Convenciones de diseño de tools y agentes multi-agente (secciones 1-2) |
| [The AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook) (Claude) | Guía de proceso para desarrollar con agentes de código | Prácticas de feedback loop, guardrails-as-code, disciplina de `CLAUDE.md` (sección 5) — **no** el esquema `intent.md`/`spec.md`/`plan.md` completo |
| [AratKruglik/claude-sdlc](https://github.com/AratKruglik/claude-sdlc) | Plugin de Claude Code que orquesta un pipeline BA→Dev→QA→Security→Docs por stack | Idea de tiering de modelo por tipo de tarea (ya la aplicamos) — **no** el plugin en sí ni su pipeline de fases |

Explícitamente **no** adoptamos de estas fuentes (ver también "Qué NO
hacer" en `CLAUDE.md`):
- El split `intent.md` → `spec.md` → `plan.md` con gates separados: este
  proyecto usa un solo `PLAN.md`, a propósito.
- El plugin marketplace / pipeline de 5 fases de `claude-sdlc`: es una
  herramienta para repos grandes con múltiples equipos; acá agrega
  proceso sin agregar valor.
- Cualquier patrón de scoring o clasificación de usuario que aparezca en
  ejemplos de "evaluación" de agentes — sigue prohibido por la sección de
  privacidad del spec, sin excepción por venir de una fuente "oficial".

## 1. Diseño de tools (Strands SDK)

Basado en la documentación de `strands-agents/sdk-python` y en el patrón
que ya siguen `tools/ficha.py`, `tools/perfil.py`, `tools/crisis.py`.

- **Docstring de cada `@tool` debe cubrir 5 cosas**: para qué sirve,
  cuándo usarla, qué formato tienen sus parámetros, qué formato tiene su
  salida, y qué limitaciones tiene. Un docstring de una línea no alcanza
  si el modelo tiene que decidir *cuándo* invocarla (compará
  `crear_tool_presentar_opciones` en `agents/_modelo.py`, que sí lo hace,
  contra cualquier tool nueva que se agregue sin ese detalle).
- **Parámetros determinísticos nunca van en la firma del `@tool`.** Si un
  valor no debe quedar a criterio del modelo (`usuario_id`, `fase`), se
  fija por *closure* al construir el tool dentro de `agents/*.py`, como ya
  hace cada agente con `guardar_ficha_usuario`. El módulo base en
  `tools/*.py` expone la función sin decorar; el decorador y el closure
  viven en el agente que la usa. No dupliques esta explicación en cada
  archivo nuevo — enlazá a `tools/ficha.py` como referencia.
- **Un tool, una responsabilidad.** Si una tool empieza a necesitar un
  parámetro tipo `modo` o `accion` para bifurcar comportamiento, son dos
  tools.
- **Nunca actives `load_tools_from_directory=True`** sin auditar antes qué
  hay en ese directorio — cualquier `.py` ahí se ejecuta. No lo usamos
  hoy; si alguien lo agrega, que sea una decisión explícita, no un
  default heredado de un ejemplo.
- **Siempre kwargs al invocar un tool directamente como método** (fuera
  del loop del agente, ej. en tests) — Strands no soporta posicionales
  ahí.
- **Guardrails que no pueden fallar van en código, no en prompt.**
  `tools/crisis.py` es el ejemplo a replicar: detección por regex
  determinística, sin llamada a modelo, corre siempre sin importar el
  idioma seleccionado. Cualquier guardrail nuevo con la misma criticidad
  (ej. detección de otro tipo de contenido sensible) sigue ese patrón, no
  el de "instrucción fuerte en el system prompt".

## 2. Diseño de agentes y multi-agente (Strands SDK)

- **Patrón agents-as-tools para orquestación**, que es exactamente lo que
  hace `agents/orquestador_agente.py` desde el commit `953c711`: un
  agente orquestador con juicio semántico, cada fase expuesta vía
  `Agent.as_tool()`, nunca dispatch por regex/diccionario de fase. Si se
  agrega un agente nuevo al flujo, sigue este mismo patrón — no un
  `if/elif` de fase.
- **Responsabilidad acotada por agente.** Cada uno de los 5 agentes de
  fase tiene un system prompt enfocado en su propio trabajo; las reglas
  transversales (tono, el informe estructurado al orquestador) viven una
  sola vez en `agents/_modelo.py` (`REGLA_CONJUGACION_ES`,
  `INSTRUCCION_INFORME_ES/EN`) y se inyectan por composición de string,
  no copiadas en cada prompt. Mantené esto — es lo que evita que un fix
  de bug tenga que aplicarse a mano 5 veces (encontramos exactamente esa
  duplicación una vez ya en `_INSTRUCCION_INFORME_*`, corregida al
  escribir este documento — ver el commit que la centraliza).
- **`preserve_context` es una decisión explícita, no un default.** Si un
  agente de fase necesita recordar turnos previos dentro de la misma
  invocación del orquestador, hay que decidirlo a propósito y dejar
  constancia de por qué (afecta costo y puede filtrar contexto entre
  fases que el spec quiere separadas).
- **La persistencia de sesión es propia, no la clase `SessionManager` de
  Strands.** `SesionTelos` (`agents/orquestador.py`) reconstruye a mano
  los mensajes de cada fase (`tools/conversacion.py` → `Agent(messages=
  ...)`) y versiona la ficha por separado (`tools/ficha.py`) directo
  sobre `bedrock_agentcore.memory.MemoryClient` — no sobre el
  `AgentCoreMemorySessionManager` que ofrece Strands. Es a propósito:
  ese `SessionManager` solo soporta un agente por sesión, y Telos corre
  5 `Agent` distintos (uno por fase, reconstruido cada turno) más un
  objeto de dominio versionado (la ficha, con fusión de claves) y una
  lista de insights que cruza las 5 fases — nada de eso es "historial de
  conversación" en el sentido que el `SessionManager` genérico persiste.
  Si el diseño alguna vez colapsa a un solo agente de larga vida por
  usuario, vale la pena reconsiderarlo; con el diseño multi-agente
  actual, adoptarlo forzaría la arquitectura en vez de simplificarla.
  Los agentes de fase, en cualquier caso, nunca deben tener su propio
  `SessionManager` si en algún momento se usa uno — dos fuentes de
  verdad sobre qué se guardó producen el tipo de bug que ya documentó
  `guardar_ficha_usuario_fusionada` en `tools/ficha.py`.
- **Nunca mutar `agent.messages` directamente** para inyectar contexto —
  no se persiste. Si un agente necesita ver hechos de conversaciones
  anteriores (como ya hace el orquestador con `insights_conocidos`),
  se pasan compuestos en el system prompt en el momento de construir el
  `Agent`, igual que ahora.
- **Antes de guardar en AgentCore Memory, podar/resumir turnos viejos**
  si la conversación crece mucho (tool-heavy agents acumulan historial
  rápido) — aplica directo a la Prioridad 2 de `CLAUDE.md` (persistencia
  vía AgentCore Memory). No hace falta resolverlo ahora si no hay
  volumen real todavía, pero cualquier implementación del Agente 5 /
  Vista de resumen debería tener en cuenta que el historial crudo no es
  lo que se persiste tal cual para siempre.

## 3. Integración con AgentCore (AWS)

Relevante para la Prioridad 2 de `CLAUDE.md` (Memory) y la Prioridad 5
(Gateway de calendario) cuando se retomen.

- **Selector de backend local/agentcore como único patrón de
  persistencia**, ya establecido por `ficha.py`/`perfil.py`/
  `conversacion.py`/`push_suscripcion.py`. Cualquier tool nueva que
  necesite persistencia sigue el mismo esqueleto: módulo base sin
  decorar + `_local.py` + `_agentcore.py`, selector por
  `TELOS_*_BACKEND` env var. No inventes un mecanismo de selección
  distinto para un tool nuevo.
- **Desarrollo local antes que nube real.** El patrón de AWS con la CLI
  `agentcore` (`create`/`dev`/`deploy`/`invoke`) confirma lo que ya
  hacemos con el backend `local`: todo el flujo de agentes tiene que
  poder probarse con `TELOS_FICHA_BACKEND=local` (y equivalentes) sin
  credenciales de AWS. Los tests en `tests/` no deben requerir AWS real
  — ya es una regla en `CLAUDE.md`, esto la refuerza desde el lado de
  "así lo hace también AWS en sus propios samples".
- **Gateway (calendario, Prioridad 5) se modela como tool MCP**, no como
  llamada HTTP directa embebida en un agente — es el patrón que
  `agentcore-samples` usa para convertir APIs/Lambdas en tools
  compatibles con MCP. Si se implementa antes de que sobre tiempo,
  arrancar ahí en vez de escribir un cliente HTTP ad-hoc dentro de
  `tools/calendario.py`.
- **IaC aditiva, nunca compartida entre Streamlit y la migración**,
  que es justo cómo ya está armado `infra/stacks/telos_stack.py` — instancia
  y CloudFront propios para `api/`+`web/`, sin tocar lo de Streamlit.
  Mantené esa separación si se agrega infra nueva para Memory/Gateway.
- **Observabilidad vía OpenTelemetry cuando se despliegue a AgentCore
  Runtime** (Prioridad 5, opcional) — no es urgente para el MVP, pero si
  se activa, que sea trace/log estructurado, no `print()` disperso.

## 4. Model tiering

Ya está resuelto correctamente en `agents/_modelo.py` — se documenta acá
para que no se reinvente al agregar un agente nuevo:

- **Sonnet** para el único punto de contacto con la entrada/salida real
  de la persona y con juicio de enrutamiento (el orquestador).
- **Haiku** para trabajo de contenido acotado por un prompt específico
  (cada fase). Si un agente nuevo tiene un prompt enfocado y no decide
  flujo, arranca en Haiku, no en Sonnet por default.
- Justificar en un comentario, como ya se hace, *por qué* ese tier —
  no repetir la tabla de precios de Bedrock en cada archivo, solo la
  decisión y su motivo.

## 5. Flujo de trabajo con Claude Code (adaptado del AI-Native SDLC Playbook)

Adoptamos las prácticas de proceso que no chocan con "un solo PLAN.md" ni
con el tamaño de este proyecto:

- **Plan mode antes de cambios no triviales.** Para cualquier cambio que
  toque el guardrail de crisis, persistencia (`ficha`/`perfil`/
  `conversacion`), o las reglas de tono del Agente 5, pasar primero por
  un plan explícito y validado antes de escribir código — no directo a
  editar.
- **Regla de `CLAUDE.md`: si un error se repite dos veces, la corrección
  va a `CLAUDE.md` (o al comentario del módulo si es específico de un
  archivo).** Ya se hace de forma orgánica — ver los comentarios de
  "bug real" en `agents/_modelo.py` (`REGLA_CIERRE_REAL_ES`,
  `REGLA_TRANSICION_ES`) y `tools/ficha.py`
  (`guardar_ficha_usuario_fusionada`). Seguir documentando el bug real
  que motivó cada regla nueva, no solo la regla — es lo que permite
  juzgar después si sigue aplicando.
- **Feedback loop verificable en cada cambio.** `pytest` tiene que poder
  correr sin credenciales de AWS (ya es regla) y sin red. Para un fix de
  bug de comportamiento del agente, reproducir primero con
  `simular_conversacion.py` o un test dedicado, confirmar que falla por
  la razón esperada, recién después arreglar.
- **Guardrails de proceso como código, no como hábito.** El mismo
  principio de `tools/crisis.py` (determinístico, no depende de que el
  LLM decida bien) aplica al proceso de desarrollo: si algo "no se debe
  hacer nunca" (agregar `Co-Authored-By`, commitear `CLAUDE.md`/
  `PLAN.md`, meter secretos en docs públicos), que esté en
  `.gitignore`/hooks donde sea posible, no solo en una instrucción que
  hay que recordar.
- **Revisión antes de mergear cambios de riesgo alto.** Usar
  `/code-review` (o `/code-review ultra` para cambios grandes) en
  cualquier PR que toque guardrails, persistencia o tono del Agente 5 —
  las tres áreas marcadas como no negociables en `CLAUDE.md`.
- **Ningún agente con credenciales de producción de larga duración.**
  Si en algún momento se automatiza deploy o se le da a un agente acceso
  de escritura a AWS, que sea con credenciales de corta vida y detrás de
  un gate humano explícito para producción — nunca acceso directo desde
  una sesión de agente a un recurso productivo.

## 6. Cómo se va a revisar esto

La próxima tarea de revisión de código va a usar este documento como
checklist, sección por sección, contra el estado real de `agents/` y
`tools/`. Donde el código ya cumple (la mayoría de las secciones 1-4,
porque estos lineamientos se escribieron mirando el código existente),
la revisión debería confirmarlo explícitamente, no solo buscar
incumplimientos.
