# Telos

> El propósito no es una meta a alcanzar, es un horizonte que el sistema
> diario acerca.

Telos es un agente conversacional que acompaña a una persona a través de 4
fases fijas — explorar, sintetizar, validar y convertir en sistema — hasta
llegar a un propósito de vida concreto y un sistema de 4 preguntas
accionable. Después, un quinto agente hace seguimiento breve cada vez que
la persona vuelve a conversar, sin rachas ni gamificación.

Construido para el hackathon AWS Agents for Humans (track Everyday
Agents) con [Strands Agents SDK](https://github.com/strands-agents/harness-sdk),
Amazon Bedrock y AWS CDK.

## Arquitectura

```
Usuario
  │
  ▼
[Orquestador] ──(cada turno)──> detectar_señal_crisis (código, no LLM)
  │                                   │
  │                              (si dispara)
  │                                   ▼
  │                          Mensaje fijo de crisis
  │                          (corta el flujo normal)
  │
  ├─ fase 1 ─> Explorador           ─┐
  ├─ fase 2 ─> Sintetizador          │  flujo fijo,
  ├─ fase 3 ─> Coach de Validación   │  no se saltan fases
  ├─ fase 4 ─> Estratega de Sistemas─┘──> ficha completa
  │                                                │
  └─ fase 5 ─> Seguimiento (al abrir sesión) <─────┘
                    │
                    └─(si el sistema ya no sirve)─> re-entra a Fase 3 o 4
```

Cada agente de fase es un `strands.Agent` independiente (`agents/*.py`)
con su propio system prompt — el detalle completo de prompts, tools,
reglas de tono y privacidad vive en
[`docs/agente-proposito-de-vida-prompts.md`](docs/agente-proposito-de-vida-prompts.md),
la fuente de verdad de esta arquitectura.

La persistencia de la ficha (`tools/ficha.py`) es intercambiable entre un
backend JSON local (desarrollo) y AgentCore Memory real (producción) sin
tocar los agentes — ver [Persistencia](#persistencia) abajo.

## Estructura del repo

```
/agents/     agentes de Strands, uno por archivo (+ _modelo.py compartido)
/tools/      tools de los agentes: ficha, crisis, calendario
/ui/         interfaz Streamlit (100% Python)
/infra/      stack de AWS CDK (Python)
/docs/       spec de arquitectura de agentes
```

## Correr localmente

Requiere Python 3.12+ y credenciales de AWS con acceso a Bedrock
(`aws configure` o variables de entorno estándar).

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows; en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
TELOS_REQUIRE_LOGIN=0 streamlit run ui/app.py
```

Por defecto usa el backend JSON local para la ficha
(`data/fichas.json`, gitignored) — no hace falta AgentCore Memory para
probar el flujo de las 4 fases. `TELOS_REQUIRE_LOGIN=0` salta el login de
Google (que necesita Cognito desplegado, ver [Autenticación](#autenticación))
y vuelve a mostrar el campo de identificador libre.

### Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `TELOS_MODEL_ID` | `anthropic.claude-sonnet-4-5-20250929-v1:0` | Modelo de Bedrock que usan los 5 agentes |
| `TELOS_AWS_REGION` | `us-east-1` | Región de Bedrock / AgentCore |
| `TELOS_FICHA_BACKEND` | `local` | `local` (JSON) o `agentcore` (AgentCore Memory real) |
| `TELOS_MEMORY_NAME` | `telos_fichas_usuario` | Nombre del recurso de AgentCore Memory (solo si `TELOS_FICHA_BACKEND=agentcore`) |
| `TELOS_REQUIRE_LOGIN` | `1` | `0` para saltar el login de Google en local |
| `COGNITO_DOMAIN`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `APP_URL` | — | Los inyecta `cdk deploy` como env vars de App Runner; solo hace falta exportarlos a mano si corrés el login localmente |

## Persistencia

`tools/ficha.py` es un selector: importa el backend real
(`tools/ficha_local.py` o `tools/ficha_agentcore.py`) según
`TELOS_FICHA_BACKEND`. Los agentes siempre importan desde `tools/ficha.py`,
nunca de los backends directamente, así que cambiar de backend no toca
`agents/*.py`.

**Estado del backend de AgentCore Memory:** implementado
(`tools/ficha_agentcore.py`, cada versión de la ficha se guarda como un
blob event) pero no probado todavía contra un recurso real de AWS — este
entorno de desarrollo no tenía credenciales de AWS al escribirlo. Antes
del demo, correr con `TELOS_FICHA_BACKEND=agentcore` en un entorno con
credenciales reales (ej. CloudShell) y confirmar que
`guardar_ficha_usuario` / `leer_ficha_usuario` funcionan de punta a punta.

## Autenticación

Login con Google vía Cognito Hosted UI (`ui/auth.py`, recursos en
`infra/stacks/telos_stack.py`). Requiere un paso manual que **solo vos
podés hacer** (no hay tool de AWS ni de este repo que lo automatice):

### 1. Crear el OAuth Client en Google Cloud Console

1. [console.cloud.google.com](https://console.cloud.google.com/) → crear
   o elegir un proyecto.
2. **APIs & Services → OAuth consent screen** — configurarla (External,
   modo Testing alcanza para el demo).
3. **APIs & Services → Credentials → Create Credentials → OAuth client
   ID** → tipo **Web application**.
4. En **Authorized redirect URIs** todavía no vas a tener el dato — hacé
   el paso 2 (deploy) primero, el output `GoogleRedirectUriParaConsola`
   te da la URL exacta para pegar acá (algo como
   `https://telos-<cuenta>.auth.<región>.amazoncognito.com/oauth2/idpresponse`).
   Guardá el Client ID y el Client Secret que te da Google.

### 2. Deploy (dos pasadas — ver por qué en el comentario del stack)

```bash
cd infra
pip install -r requirements.txt
npx aws-cdk bootstrap   # solo la primera vez en la cuenta/región

# Primera pasada: crea todo, pero el callback de Cognito todavía apunta
# a un placeholder porque la URL de App Runner no existe hasta ahora.
npx aws-cdk deploy \
  --parameters GoogleClientId=<client id de Google> \
  --parameters GoogleClientSecret=<client secret de Google>
```

Con los outputs de esa primera pasada: pegá `GoogleRedirectUriParaConsola`
en Google Cloud Console (paso 1.4), y guardá `UrlServicioUI`.

```bash
# Segunda pasada: ahora sí, con la URL real de App Runner.
npx aws-cdk deploy \
  --parameters GoogleClientId=<client id de Google> \
  --parameters GoogleClientSecret=<client secret de Google> \
  --parameters AppUrl=<el UrlServicioUI del paso anterior>
```

A partir de acá, `usuario_id` en la app es el email de la cuenta de
Google con la que se loguea la persona (ya no el campo de texto libre).

## Guardrail de crisis

`tools/crisis.py::detectar_señal_crisis` es determinístico (sin llamada a
modelo) y el Orquestador lo evalúa en cada turno, antes de rutear a
cualquier agente — nunca es una tool que el modelo pueda decidir no
llamar. Ver sección 10 del spec para el mensaje fijo y los recursos de
ayuda (Latam/España).

## Despliegue (desde AWS CloudShell)

El despliegue usa dos mecanismos separados a propósito, para no mezclar
CDK con recursos de AgentCore que CloudFormation no modela de forma
nativa:

1. **CDK** — IAM, la imagen Docker de la UI (build automático vía
   `DockerImageAsset`, necesita Docker disponible en CloudShell) y el
   hosting en App Runner:

   ```bash
   cd infra
   pip install -r requirements.txt
   npx aws-cdk bootstrap   # solo la primera vez en la cuenta/región
   npx aws-cdk deploy
   ```

   Al terminar, el output `ArnRolAgentes` da el ARN del rol IAM con
   permisos de Bedrock/AgentCore para reutilizar en el paso 2, y
   `UrlServicioUI` la URL pública del App Runner con la interfaz
   Streamlit.

2. **AgentCore Runtime / Memory / Gateway** — vía el toolkit de AgentCore,
   reutilizando el rol IAM que CDK ya creó:

   ```bash
   agentcore configure
   agentcore launch
   ```

   (Pendiente de documentar el detalle exacto de flags una vez probado
   en CloudShell — ver "Qué falta" abajo.)

## Qué falta / limitaciones conocidas

- Backend de AgentCore Memory sin probar contra AWS real (ver
  [Persistencia](#persistencia)).
- Login con Google/Cognito implementado pero sin probar contra un
  despliegue real (necesita el Client ID/Secret de Google + las dos
  pasadas de deploy, ver [Autenticación](#autenticación)).
- `COGNITO_CLIENT_SECRET` viaja como variable de entorno en texto plano
  en App Runner (no Secrets Manager) — aceptable para el MVP, no queda
  expuesto fuera de la cuenta de AWS, pero es lo primero a endurecer si
  esto pasa de demo a algo real.
- `crear_evento_calendario` está mockeado (P2 en PLAN.md) — devuelve una
  confirmación simulada, no crea eventos reales en Google Calendar.
- El seguimiento (Fase 5) se dispara "al abrir conversación", no hay
  scheduler real que envíe recordatorios proactivos.
- El paso 2 del despliegue (`agentcore configure`/`launch`) no se ha
  ejercitado todavía end-to-end.

## Licencia

MIT — ver [LICENSE](LICENSE).
