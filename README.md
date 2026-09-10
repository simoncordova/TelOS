# Telos

> El propósito no es una meta a alcanzar, es un horizonte que el sistema
> diario acerca.

Telos es un agente conversacional que acompaña a una persona a través de 4
fases fijas — explorar, sintetizar, validar y convertir en sistema — hasta
llegar a un propósito de vida concreto y un sistema de 4 preguntas
accionable. Después, un quinto agente hace seguimiento breve cada vez que
la persona vuelve a conversar, sin rachas ni gamificación. Disponible en
español e inglés (selector explícito en la UI).

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
la fuente de verdad de esta arquitectura. Las reglas compartidas por los
5 (idioma neutro) viven en un solo lugar (`agents/_modelo.py`), y un hook
de Strands (`agents/_calidad.py`) verifica de forma determinística la
respuesta generada y fuerza una regeneración si hace falta — no es el
modelo autoevaluándose, es un chequeo por código, igual que el guardrail
de crisis.

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
(`aws configure` o variables de entorno estándar). Si preferís no generar
keys locales, saltate esta sección y probá directo desde CloudShell — ver
[Probar contra Bedrock real desde CloudShell](#probar-contra-bedrock-real-desde-cloudshell)
más abajo, que usa las credenciales temporales de la sesión del console.

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows; en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
TELOS_REQUIRE_LOGIN=0 streamlit run ui/app.py
```

Por defecto usa el backend JSON local para la ficha
(`data/fichas.json`, gitignored) — no hace falta AgentCore Memory para
probar el flujo de las 4 fases. `TELOS_REQUIRE_LOGIN=0` salta el login
(que necesita Cognito desplegado, ver [Autenticación](#autenticación))
y vuelve a mostrar el campo de identificador libre.

### Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `TELOS_MODEL_ID` | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | Modelo de Bedrock que usan los 5 agentes — inference profile "global", no el ID pelado (ese falla con `ValidationException` en la mayoría de las regiones, Sonnet 4.5 no admite invocación on-demand directa) |
| `TELOS_AWS_REGION` | `us-east-1` | Región de Bedrock / AgentCore |
| `TELOS_FICHA_BACKEND` | `local` | `local` (JSON) o `agentcore` (AgentCore Memory real) |
| `TELOS_MEMORY_NAME` | `telos_fichas_usuario` | Nombre del recurso de AgentCore Memory (solo si `TELOS_FICHA_BACKEND=agentcore`) |
| `TELOS_REQUIRE_LOGIN` | `1` | `0` para saltar el login en local |
| `COGNITO_DOMAIN`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`, `APP_URL` | — | Los inyecta `cdk deploy` en el `docker run` del user data de la instancia EC2; solo hace falta exportarlos a mano si corrés el login localmente |

## Probar contra Bedrock real desde CloudShell

Antes de meterse con el deploy completo (CDK + Cognito), vale la
pena validar que los agentes conversan bien contra el modelo real. Esto
todavía no se probó ni una vez — es lo primero que yo revisaría.

CloudShell no necesita ninguna key: usa las credenciales temporales de tu
sesión del console automáticamente.

1. **Confirmar que tu identidad de CloudShell puede usar el modelo.** Ya
   no existe el toggle manual de "Model access" en la consola — Bedrock
   auto-suscribe el modelo la primera vez que se invoca, siempre que la
   identidad que hace esa primera llamada tenga, además de
   `bedrock:InvokeModel`, el permiso `aws-marketplace:Subscribe` (el rol
   de CloudShell suele tenerlo si administrás la cuenta; si no, alguien
   con esos permisos hace esa primera invocación una sola vez y después
   queda habilitado para toda la cuenta).
2. **En CloudShell, instalar dentro de un entorno virtual** — CloudShell
   viene con `aws-sam-cli` preinstalado, que fija versiones exactas de
   `boto3`/`watchdog`; instalar sin venv termina pisando esas versiones
   globalmente (`pip` tira un warning de conflicto, no rompe nada de
   Telos, pero puede afectar al `sam` CLI si lo usás después en esa
   misma sesión):
   ```bash
   git clone https://github.com/simoncordova/TelOS.git
   cd TelOS
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python scripts/chat_terminal.py                  # español (default)
   python scripts/chat_terminal.py mi-usuario en     # English
   ```
   Esto abre un chat de terminal (sin Streamlit, sin browser) contra los
   agentes reales. Escribe como si fueras un usuario explorando su
   propósito; `ficha` muestra el estado guardado y `salir` termina.

Si algo se ve raro (una fase no cierra, el guardrail no dispara cuando
debería, el tono no cuadra), avísame con lo que viste y ajustamos el
prompt correspondiente en `docs/agente-proposito-de-vida-prompts.md` +
`agents/*.py`.

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

La ficha guarda el resultado final de cada fase, una sola vez, al
cerrarla — no alcanza para reconstruir la conversación si el proceso se
corta a mitad de una fase (se cae, CloudShell recicla la sesión, se
cierra el navegador). Para eso existe `tools/conversacion.py` (mismo
patrón selector, mismo `TELOS_FICHA_BACKEND`): guarda cada turno de la
fase en curso vía AgentCore Memory (`create_event`, eventos
conversacionales de verdad — no `create_blob_event`, que es lo que usa
la ficha) y el Orquestador los precarga como historial real del agente
al construirlo o reconstruirlo. Mismo estado que el backend de la
ficha: implementado (`tools/conversacion_agentcore.py`) pero sin probar
contra AWS real todavía.

## Autenticación

Login vía Cognito Hosted UI (`ui/auth.py`, recursos en
`infra/stacks/telos_stack.py`) con usuarios propios del User Pool — sin
ningún proveedor externo (nada de Google/Facebook/etc.), para no
depender de ninguna cuenta de terceros. No hay registro público
(`self_sign_up_enabled=False`): el dueño de la cuenta crea los usuarios
de prueba a mano con `aws cognito-idp admin-create-user`. `usuario_id`
en la app es el email de esa cuenta. El comando exacto está en
[Despliegue](#despliegue) abajo.

## Guardrail de crisis

`tools/crisis.py::detectar_señal_crisis` es determinístico (sin llamada a
modelo) y el Orquestador lo evalúa en cada turno, antes de rutear a
cualquier agente — nunca es una tool que el modelo pueda decidir no
llamar. Revisa patrones en **español e inglés siempre**, sin importar el
idioma seleccionado en la UI — es una cuestión de seguridad, no de
preferencia. Solo el mensaje de respuesta usa el idioma seleccionado:
recursos Latam/España en español, 988 Suicide & Crisis Lifeline
(EE.UU./Canadá) en inglés. Ver sección 10 del spec.

## Protecciones de costo

Cuatro capas, pensadas para que ni un uso descuidado ni uno malicioso
disparen la cuenta de AWS sin que nadie se entere:

- **Login obligatorio** (`TELOS_REQUIRE_LOGIN`, default `"1"`): nadie
  llega al chat, y por lo tanto a Bedrock, sin loguearse con un usuario
  de Cognito creado a mano — no hay registro público
  (`self_sign_up_enabled=False`).
- **Límite de 100 invocaciones reales por usuario por día**
  (`tools/limite_uso.py`): cuenta cada invocación real al modelo, no
  cada mensaje que escribe la persona (una cascada de cambio de fase
  dispara más de una invocación por mensaje, y cada una cuesta igual).
  Al llegar al límite, corta antes de tocar Bedrock y devuelve un aviso
  fijo. Protege contra un usuario de prueba (o su contraseña filtrada)
  mandando mensajes sin parar — no contra el resto de riesgos de abajo.
- **Un solo servidor, sin auto-scaling** (`ec2.Instance` en
  `infra/stacks/telos_stack.py`, un `t3.micro`, no un Auto Scaling
  Group): alcanza de sobra para 3 usuarios de prueba, y no hay forma de
  que tráfico anómalo escale cómputo de más — no existe ningún mecanismo
  de escalado que dispare, es literalmente un solo servidor prendido.
- **IAM de Bedrock delimitado al modelo exacto que usa la app**
  (`RolEjecucionAgentes`, mismo stack): antes era `resources=["*"]`
  (cualquier modelo de Bedrock); ahora son las 3 sentencias que
  documenta AWS para perfiles de inferencia cross-region "global."
  (perfil regional + modelo regional + modelo global), apuntando al
  Sonnet 4.5 que define `agents/_modelo.py`. Si el modelo cambia, esta
  política hay que actualizarla a mano — es un trade-off consciente
  frente a dejarlo abierto.
- **Alarma de AWS Budgets** (`EmailAlertaPresupuesto`, parámetro
  obligatorio del stack): avisa por email al 80% del gasto real y al
  100% del gasto proyectado del mes. Es de cuenta completa, no
  delimitada a Telos — filtrar por tag en Budgets requiere activar Cost
  Allocation Tags a mano en Billing primero, fuera del alcance de CDK.
  Es el respaldo si las capas de arriba fallan o no alcanzan, no la
  primera línea de defensa.

## Despliegue

Todo desde AWS CloudShell (sin generar keys locales — ver
[Probar contra Bedrock real desde CloudShell](#probar-contra-bedrock-real-desde-cloudshell),
que conviene hacer antes de esto). AgentCore Memory no necesita un paso
de deploy aparte: `tools/ficha_agentcore.py` crea el recurso solo, la
primera vez que se guarda o lee una ficha (por eso el primer mensaje que
alguien mande en producción puede tardar hasta ~1 minuto más de lo
normal — está creando la Memory, no es un cuelgue).

**Hosting de la UI: EC2 detrás de CloudFront, no App Runner.** La
primera versión de este stack usaba App Runner, pero AWS lo bloqueó en
una cuenta real con más de un mes de antigüedad ("The AWS Access Key Id
needs a subscription for the service") por seguir consumiendo créditos
de Free Tier sin un método de pago verificado — App Runner no tiene
nivel gratuito. EC2 (`t3.micro`) sí es Free Tier real y no pegó contra
ese bloqueo. CloudFront va adelante para dar el HTTPS automático
(dominio `*.cloudfront.net`) que perdíamos al bajar a EC2 pelado —
Cognito exige HTTPS en las callback URLs salvo para `localhost`, así que
esto no es opcional. Si tu cuenta ya tiene App Runner habilitado, no
hace falta este rodeo, pero el stack no lo vuelve a intentar por
default.

### Paso 1 — CDK, primera pasada

```bash
git clone https://github.com/simoncordova/TelOS.git   # si no lo hiciste ya
cd TelOS/infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npx aws-cdk bootstrap   # solo la primera vez en la cuenta/región
npx aws-cdk deploy --parameters EmailAlertaPresupuesto=<tu-email>
```

`EmailAlertaPresupuesto` es obligatorio (sin default a propósito, ver
[Protecciones de costo](#protecciones-de-costo)) — ahí llega la alarma
de AWS Budgets. Esta primera pasada crea todo (IAM, Cognito, ECR, VPC,
EC2, CloudFront, Budget) pero el callback de Cognito todavía apunta a un
placeholder, porque la URL real de CloudFront recién se conoce después
de crearla. Guarda los outputs `UrlServicioUI` y `UserPoolId` para los
pasos siguientes.

CloudFront tarda varios minutos en propagarse después del deploy (a
veces 10-15) — si al entrar a `UrlServicioUI` da error al toque, espera
un rato antes de asumir que algo salió mal. Si el chat nunca arranca
después de eso, `IdInstanciaUI` (otro output) sirve para entrar a la
instancia sin SSH: `aws ssm start-session --target <IdInstanciaUI>` y
revisar `docker ps` / `docker logs <container>` ahí adentro — el user
data corre `dnf`, `docker login` y `docker run` en la primera
inicialización, y si algo de eso falla en silencio, es el lugar donde
mirar.

### Paso 2 — CDK, segunda pasada (con la URL real)

```bash
npx aws-cdk deploy --parameters AppUrl=<el UrlServicioUI del paso anterior>
```

### Paso 3 — Crear los usuarios de prueba

Sin registro público, así que los usuarios se crean a mano (con las
credenciales de sesión de CloudShell, sin generar ninguna key nueva):

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <el UserPoolId del Paso 1> \
  --username usuario1@ejemplo.com \
  --user-attributes Name=email,Value=usuario1@ejemplo.com Name=email_verified,Value=true \
  --temporary-password "CambiaEsto123!"
```

Repetí para los 3 usuarios de prueba. Cada persona, al loguearse por
primera vez en el Hosted UI con esa contraseña temporal, Cognito le va a
pedir que la cambie por una definitiva — es el flujo normal, no hace
falta hacer nada extra.

### Paso 4 — Abrir la app

Entrá a `UrlServicioUI`, iniciá sesión con uno de los usuarios de
prueba, y recorré las 4 fases. El rol IAM (`ArnRolAgentes`) ya tiene
todos los permisos que necesita (Bedrock + AgentCore Memory) — no hace
falta nada más para que la app funcione de punta a punta.

### (Opcional, no bloquea nada) — AgentCore Runtime real

Bonus de puntaje ("Technical Implementation" del reglamento del
hackathon), no un requisito: hospedar el código de agentes en AgentCore
Runtime en vez de correrlo en el mismo contenedor de la UI. Reutiliza el rol de
`ArnRolAgentes` como execution role:

```bash
agentcore configure
agentcore launch
```

Sin probar todavía end-to-end — ver "Qué falta" abajo.

## Qué falta / limitaciones conocidas

- Backend de AgentCore Memory sin probar contra AWS real, tanto para la
  ficha como para el historial de turnos (ver [Persistencia](#persistencia)).
- Login con Cognito implementado pero sin probar contra un despliegue
  real (necesita las dos pasadas de deploy + crear los usuarios de
  prueba, ver [Autenticación](#autenticación)).
- `COGNITO_CLIENT_SECRET` viaja como variable de entorno en texto plano
  dentro del contenedor Docker (embebido en el user data de la instancia
  EC2, no Secrets Manager) — aceptable para el MVP, no queda expuesto
  fuera de la cuenta de AWS, pero es lo primero a endurecer si esto pasa
  de demo a algo real.
- Security group de la instancia EC2 abierto a cualquier IP en el puerto
  8501, no delimitado al rango de CloudFront (ver
  [Protecciones de costo](#protecciones-de-costo)) — el login de Cognito
  sigue aplicando igual, pero es una mejora obvia si sobra tiempo.
- `crear_evento_calendario` está mockeado — devuelve una confirmación
  simulada, no crea eventos reales en Google Calendar.
- El seguimiento (Fase 5) se dispara "al abrir conversación", no hay
  scheduler real que envíe recordatorios proactivos.
- El paso opcional de AgentCore Runtime (`agentcore configure`/`launch`)
  no se ha ejercitado todavía — no bloquea el despliegue principal, es
  bonus de puntaje.

## Licencia

MIT — ver [LICENSE](LICENSE).
