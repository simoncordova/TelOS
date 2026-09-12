"""Stack de CDK para Telos. Ver Paso 4 del plan de implementación.

Cubre lo "clásico": IAM, build/push de la imagen de la UI, hosting en
EC2 detrás de CloudFront (ver nota abajo sobre por qué no App Runner), y
autenticación (Cognito, usuarios propios). Deliberadamente NO define
recursos AWS::BedrockAgentCore::* — Runtime/Memory/Gateway se configuran
aparte con `agentcore configure` / `agentcore launch` desde CloudShell,
reutilizando el rol IAM que este stack deja creado (ver output
ArnRolAgentes). Documentado en el README como dos pasos de deploy
separados, no uno solo.

Hosting: EC2 (`t3.micro`, un solo `AWS::EC2::Instance`, sin Auto Scaling
Group) detrás de CloudFront, no App Runner. App Runner devolvía "The AWS
Access Key Id needs a subscription for the service" en una cuenta real
(más de un mes de antigüedad, pero todavía consumiendo créditos de Free
Tier sin haber cargado un método de pago verificado) -- App Runner no
tiene nivel gratuito y AWS lo bloquea hasta verificar pago, algo fuera
del control de este stack. EC2 sí es Free Tier real (750 hs/mes de
t2.micro o t3.micro) y no pegó contra ese bloqueo. Un solo `Instance` (no
un ASG) ya cumple el tope de "nunca más de 1" que antes hacía el
AutoScalingConfiguration de App Runner -- no hace falta nada extra para
eso. CloudFront da el HTTPS automático (dominio `*.cloudfront.net`, sin
necesitar ACM ni un dominio propio) que perdíamos al bajar a EC2 pelado
-- Cognito exige HTTPS en las callback URLs salvo para localhost, así
que esto no es opcional.

Autenticación: Cognito con su propio User Pool (self_sign_up_enabled=
False -- no hay registro público, el dueño de la cuenta crea los
usuarios de prueba a mano con `aws cognito-idp admin-create-user`, ver
README). Sin proveedores externos (nada de Google/Facebook/etc.) a
propósito: evita cualquier dependencia con una cuenta de terceros.
Requiere un SEGUNDO deploy igual: el callback URL de Cognito tiene que
ser la URL real de CloudFront, que solo se conoce después del primer
deploy (CloudFront la genera). Ver el parámetro AppUrl más abajo.
"""

from pathlib import Path

from aws_cdk import CfnOutput, CfnParameter, Duration, RemovalPolicy, SecretValue, Stack, Tags
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from constructs import Construct

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Mismo modelo que el default de agents/_modelo.py (TELOS_MODEL_ID) -- si
# ese default cambia, este también, para que la política de IAM siga
# delimitada al modelo real que invoca la app y no se vuelva a abrir a
# "cualquier modelo" por descuido.
_MODELO_BASE = "anthropic.claude-sonnet-4-5-20250929-v1:0"
_PERFIL_INFERENCIA = f"global.{_MODELO_BASE}"


class TelosStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Tag en todos los recursos del stack: identifica a Telos en la
        # consola de AWS / Cost Explorer, separado de cualquier otra cosa
        # que haya en la cuenta.
        Tags.of(self).add("Project", "TelOS")

        # Rol que ejecuta el código de agentes -- en el MVP es el mismo
        # rol de instancia de la EC2 que corre Streamlit (ver más abajo);
        # si más adelante se despliega el Runtime de AgentCore por
        # separado, este mismo rol se puede pasar como execution role de
        # `agentcore launch` en vez de crear uno nuevo.
        rol_agentes = iam.Role(
            self,
            "RolEjecucionAgentes",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description=(
                "Permisos para invocar Bedrock y AgentCore Memory/Gateway "
                "desde el código de agentes de Telos."
            ),
        )
        # Session Manager (consola de AWS, sin SSH ni puerto 22 abierto)
        # para poder entrar a la instancia si el user data falla en
        # silencio -- AL2023 trae el agente de SSM preinstalado.
        rol_agentes.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )
        # Delimitado al modelo/perfil de inferencia que la app realmente
        # invoca (_MODELO_BASE arriba), no a "cualquier modelo de
        # Bedrock" -- las 3 sentencias son el patrón exacto que documenta
        # AWS para perfiles de inferencia cross-region "global.": perfil
        # regional, modelo regional (con condición de que venga del
        # perfil) y modelo global (sin región, requerido para el
        # ruteo cross-region).
        acciones_invocar = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        arn_perfil_regional = (
            f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/{_PERFIL_INFERENCIA}"
        )
        rol_agentes.add_to_policy(
            iam.PolicyStatement(
                sid="InvocarPerfilInferenciaRegional",
                actions=acciones_invocar,
                resources=[arn_perfil_regional],
                conditions={"StringEquals": {"aws:RequestedRegion": self.region}},
            )
        )
        rol_agentes.add_to_policy(
            iam.PolicyStatement(
                sid="InvocarModeloRegional",
                actions=acciones_invocar,
                resources=[f"arn:aws:bedrock:{self.region}::foundation-model/{_MODELO_BASE}"],
                conditions={
                    "StringEquals": {
                        "aws:RequestedRegion": self.region,
                        "bedrock:InferenceProfileArn": arn_perfil_regional,
                    }
                },
            )
        )
        rol_agentes.add_to_policy(
            iam.PolicyStatement(
                sid="InvocarModeloGlobalCrossRegion",
                actions=acciones_invocar,
                resources=[f"arn:aws:bedrock:::foundation-model/{_MODELO_BASE}"],
                conditions={
                    "StringEquals": {
                        "aws:RequestedRegion": "unspecified",
                        "bedrock:InferenceProfileArn": arn_perfil_regional,
                    }
                },
            )
        )
        rol_agentes.add_to_policy(
            iam.PolicyStatement(
                # Ya no hace falta habilitar el modelo a mano en la consola
                # (Model access) — Bedrock lo auto-suscribe en la primera
                # invocación, pero ese auto-enablement necesita este
                # permiso de Marketplace en el rol que hace la primera
                # llamada. Una vez habilitado para la cuenta, ya no hace
                # falta este permiso para invocaciones futuras, pero no
                # cuesta nada dejarlo.
                actions=["aws-marketplace:Subscribe", "aws-marketplace:ViewSubscriptions"],
                resources=["*"],
            )
        )
        rol_agentes.add_to_policy(
            iam.PolicyStatement(
                # Acciones de AgentCore Memory/Gateway: servicio nuevo,
                # confirmar nombres exactos de acción contra la
                # documentación vigente antes de endurecer a least
                # privilege. Wildcard de servicio aceptable para el MVP.
                actions=["bedrock-agentcore:*"],
                resources=["*"],
            )
        )

        # --- Alarma de costo (AWS Budgets) ---
        email_alerta_presupuesto = CfnParameter(
            self,
            "EmailAlertaPresupuesto",
            type="String",
            description=(
                "Email que recibe la alarma de AWS Budgets si el gasto de la "
                "cuenta se acerca o supera el presupuesto mensual. No tiene "
                "default a propósito: sin un email real, la alarma no sirve."
            ),
        )
        limite_presupuesto_usd = CfnParameter(
            self,
            "LimitePresupuestoMensualUsd",
            type="Number",
            default=20,
            description=(
                "Presupuesto mensual (USD) que dispara la alarma. Es un "
                "tripwire de costo de la cuenta completa (AWS Budgets no "
                "puede filtrar por tag sin activar antes Cost Allocation "
                "Tags a mano en Billing), no algo delimitado solo a Telos."
            ),
        )
        budgets.CfnBudget(
            self,
            "PresupuestoTelos",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name="telos-presupuesto-mensual",
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=limite_presupuesto_usd.value_as_number,
                    unit="USD",
                ),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=email_alerta_presupuesto.value_as_string,
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="FORECASTED",
                        comparison_operator="GREATER_THAN",
                        threshold=100,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address=email_alerta_presupuesto.value_as_string,
                        )
                    ],
                ),
            ],
        )

        # --- Autenticación: Cognito con usuarios propios ---
        app_url = CfnParameter(
            self,
            "AppUrl",
            type="String",
            default="https://localhost:8501",
            description=(
                "URL pública de la UI. El primer deploy no la conoce "
                "todavía (CloudFront la genera recién al crearse) — deja "
                "el default, y haz un segundo deploy pasando "
                "--parameters AppUrl=<el output UrlServicioUI del primer "
                "deploy> para que el login funcione de verdad."
            ),
        )
        # Declarado acá (no más abajo, junto al resto de la sección
        # Web+API) porque UserPoolClientTelos necesita registrar su
        # callback/logout URL desde el vamos -- Cognito es UN solo App
        # Client compartido por Streamlit y por la API, no uno por
        # interfaz.
        web_url = CfnParameter(
            self,
            "WebUrl",
            type="String",
            default="https://localhost",
            description=(
                "URL pública del frontend Next.js + API. El primer "
                "deploy no la conoce todavía -- deja el default, y haz "
                "un segundo deploy pasando --parameters WebUrl=<el "
                "output UrlServicioWeb del primer deploy> para que el "
                "redirect_uri de Cognito quede bien configurado."
            ),
        )

        user_pool = cognito.UserPool(
            self,
            "UserPoolTelos",
            # Sin registro público: el dueño de la cuenta crea los
            # usuarios de prueba a mano (admin-create-user), no cualquiera
            # que llegue a la URL.
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            # MVP de hackathon: permite borrar el User Pool limpiamente
            # con `cdk destroy`, no pensado para retener usuarios reales.
            removal_policy=RemovalPolicy.DESTROY,
        )

        user_pool_client = cognito.UserPoolClient(
            self,
            "UserPoolClientTelos",
            user_pool=user_pool,
            generate_secret=True,
            supported_identity_providers=[cognito.UserPoolClientIdentityProvider.COGNITO],
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
                # Un solo App Client para las dos interfaces (aditivo:
                # se agregan las URLs de la API, no se quitan las de
                # Streamlit). La API usa dos rutas distintas -- el
                # callback real (donde se procesa el `code`) y la raíz
                # (a donde vuelve un logout) -- ver ui/auth.py::
                # LOGOUT_REDIRECT_URL para por qué no puede ser la misma
                # ruta para las dos cosas.
                callback_urls=[app_url.value_as_string, f"{web_url.value_as_string}/api/auth/callback"],
                logout_urls=[app_url.value_as_string, web_url.value_as_string],
            ),
        )

        user_pool_domain = cognito.UserPoolDomain(
            self,
            "UserPoolDomainTelos",
            user_pool=user_pool,
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=f"telos-{self.account}"),
        )

        imagen_ui = ecr_assets.DockerImageAsset(
            self,
            "ImagenUI",
            directory=str(_REPO_ROOT),
            file="ui/Dockerfile",
            # .dockerignore en la raíz ya excluye .venv/.git/etc. del
            # build context; exclude= es un segundo cinturón porque CDK
            # calcula el hash del asset (para saber si hace falta
            # rebuild) recorriendo `directory` y un .venv de cientos de
            # MB ahí adentro lo vuelve lentísimo o lo cuelga.
            #
            # Fundamental (no solo performance): ui/Dockerfile solo copia
            # requirements.txt/agents//tools//ui//.streamlit/ -- todo lo
            # demás en la raíz (api/, web/, scripts/, tests/, docs/,
            # conftest.py) tiene que estar excluido de este hash aunque no
            # moleste al build en sí, porque CDK lo usa para decidir si
            # cambió la imagen. Un cambio en api/ o web/ (rama
            # gamificacion) sin este exclude cambiaba el hash igual,
            # cambiaba imagen_ui.image_uri, y por
            # user_data_causes_replacement=True terminaba reemplazando
            # -- destruyendo y recreando -- la instancia de Streamlit en
            # cada deploy de la parte nueva. Bug real, encontrado en un
            # `cdk diff` antes de aplicarlo contra la cuenta real.
            exclude=[
                ".venv",
                ".git",
                "infra",
                "data",
                "api",
                "web",
                "scripts",
                "tests",
                "docs",
                "conftest.py",
                "LICENSE",
                "**/__pycache__",
                "*.md",
            ],
        )
        # La instancia EC2 hace el pull directo de ECR (docker login +
        # docker run en el user data, ver abajo) -- antes esto lo hacía
        # un rol aparte para el build de App Runner, ya no aplica.
        imagen_ui.repository.grant_pull(rol_agentes)

        # VPC chica y propia (no ec2.Vpc.from_lookup a la default): 1 AZ,
        # solo subred pública, sin NAT Gateway -- no hay nada privado que
        # necesite salir a internet por NAT, y un NAT Gateway cuesta por
        # hora aunque no se use, algo que las protecciones de costo de
        # este stack justamente evitan en todos lados.
        vpc = ec2.Vpc(
            self,
            "VpcTelos",
            max_azs=1,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="publica", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ],
        )

        sg_instancia = ec2.SecurityGroup(
            self,
            "SgInstanciaUI",
            vpc=vpc,
            description="Permite trafico HTTP entrante a Streamlit (8501).",
            allow_all_outbound=True,
        )
        # MVP: abierto a cualquier IP, no delimitado al rango de
        # CloudFront -- el login de Cognito sigue aplicando igual si
        # alguien pega directo a la IP de la instancia sin pasar por
        # CloudFront (pierde el HTTPS, no el login). Endurecer esto con
        # el prefix list administrado de CloudFront
        # (com.amazonaws.global.cloudfront.origin-facing) es la mejora
        # obvia si sobra tiempo.
        sg_instancia.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(8501), "Streamlit (directo o via CloudFront)")

        comandos_usuario = ec2.UserData.for_linux()
        comandos_usuario.add_commands(
            "dnf install -y docker",
            "systemctl enable --now docker",
            f"aws ecr get-login-password --region {self.region} | "
            f"docker login --username AWS --password-stdin {self.account}.dkr.ecr.{self.region}.amazonaws.com",
            "docker run -d --restart unless-stopped -p 8501:8501 "
            f'-e TELOS_AWS_REGION="{self.region}" '
            '-e TELOS_FICHA_BACKEND="agentcore" '
            f'-e COGNITO_DOMAIN="{user_pool_domain.base_url()}" '
            f'-e COGNITO_USER_POOL_ID="{user_pool.user_pool_id}" '
            f'-e COGNITO_CLIENT_ID="{user_pool_client.user_pool_client_id}" '
            f'-e COGNITO_CLIENT_SECRET="{user_pool_client.user_pool_client_secret.unsafe_unwrap()}" '
            f'-e APP_URL="{app_url.value_as_string}" '
            f"{imagen_ui.image_uri}",
        )

        # Un solo Instance, no un Auto Scaling Group: ya cumple el tope
        # de "nunca más de 1" sin necesitar nada extra (antes lo hacía el
        # AutoScalingConfiguration de App Runner).
        instancia_ui = ec2.Instance(
            self,
            "InstanciaUI",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            security_group=sg_instancia,
            role=rol_agentes,
            user_data=comandos_usuario,
            # El user data (con el APP_URL/Cognito embebido en el docker
            # run) solo corre una vez, al primer arranque -- sin esto, un
            # cambio de parámetro (como AppUrl en el Paso 2) actualiza la
            # plantilla pero la instancia ya corriendo se queda sirviendo
            # con los valores viejos para siempre, aunque Cognito ya
            # tenga el callback nuevo (mismatch real que pasó en un
            # deploy real). Con esto, cualquier cambio de user data
            # reemplaza la instancia -- CloudFront apunta a
            # instance_public_dns_name, así que su origen se actualiza
            # solo en el mismo deploy.
            user_data_causes_replacement=True,
            # Sin Elastic IP a propósito (menos piezas): si esta
            # instancia alguna vez se detiene y se reinicia, la IP/DNS
            # público cambia y hay que correr `cdk deploy` de nuevo para
            # que CloudFront apunte al valor nuevo -- aceptable para el
            # MVP, que la deja corriendo sin pausar.
            associate_public_ip_address=True,
        )

        # CloudFront da el HTTPS automático (dominio *.cloudfront.net)
        # que App Runner daba gratis y EC2 pelado no -- sin esto, Cognito
        # rechaza el callback URL (exige HTTPS salvo para localhost).
        # Cache deshabilitado y todos los headers/cookies/query strings
        # reenviados: Streamlit necesita que el WebSocket (la interacción
        # del chat) y el query string ?code= del login de Cognito lleguen
        # intactos al origen, nunca cacheados.
        distribucion = cloudfront.Distribution(
            self,
            "DistribucionUI",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    instancia_ui.instance_public_dns_name,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    http_port=8501,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
        )

        CfnOutput(
            self,
            "UrlServicioUI",
            value=f"https://{distribucion.distribution_domain_name}",
            description=(
                "Pasar como --parameters AppUrl=<esta URL> en un segundo "
                "deploy para que el callback de Cognito funcione."
            ),
        )
        CfnOutput(
            self,
            "UserPoolId",
            value=user_pool.user_pool_id,
            description=(
                "Usar con `aws cognito-idp admin-create-user --user-pool-id "
                "<esto>` para crear los usuarios de prueba (ver README)."
            ),
        )
        CfnOutput(
            self,
            "ArnRolAgentes",
            value=rol_agentes.role_arn,
            description=(
                "Reutilizar como execution role en `agentcore launch` si "
                "se despliega AgentCore Runtime por separado."
            ),
        )
        CfnOutput(
            self,
            "IdInstanciaUI",
            value=instancia_ui.instance_id,
            description=(
                "Usar con `aws ssm start-session --target <esto>` para "
                "entrar a la instancia si el user data falla (ver README)."
            ),
        )

        # --- Web + API (rama gamificacion): frontend Next.js nuevo y su
        # backend delgado -- ver C:\Users\Wendy\.claude\plans\
        # cosmic-zooming-tarjan.md sección C. Instancia y distribución
        # propias, separadas de InstanciaUI/DistribucionUI a propósito:
        # así un despliegue de esta parte (incluyendo un reemplazo por
        # user_data_causes_replacement) nunca puede interrumpir la
        # instancia que sirve Streamlit -- "mantener Streamlit
        # desplegado" tiene que ser literal, no solo conceptual.
        #
        # Los dos contenedores (API :8000, Next.js :3000) comparten esta
        # misma instancia con --network host: es la forma más simple de
        # que el Next.js server (Server Components corriendo del lado
        # del server, no en el navegador) le hable a la API por
        # http://localhost:8000 sin un hop extra por CloudFront ni una
        # red Docker propia -- ver web/src/lib/api.ts. Un solo dominio de
        # CloudFront enruta `/api/*` a la API y todo lo demás a Next.js,
        # así el navegador nunca necesita CORS ni conocer dos dominios.
        #
        # Login real de Cognito activado acá (Fase 2 del plan, completa)
        # -- `web_url` ya se declaró más arriba, junto a UserPoolClientTelos,
        # porque el App Client necesita conocer esta URL desde su propia
        # construcción.

        # Fase 3 (Web Push): claves generadas UNA vez a mano con
        # scripts/generar_claves_vapid.py, nunca en el repo -- mismo
        # criterio que el client secret de Cognito. Sin default: un push
        # real necesita claves reales, no vale la pena un placeholder que
        # deje /api/push/config "configurado=true" con una clave inválida.
        vapid_public_key = CfnParameter(
            self,
            "VapidPublicKey",
            type="String",
            default="",
            description="Clave pública VAPID (scripts/generar_claves_vapid.py). Vacío = push deshabilitado.",
        )
        vapid_private_key = CfnParameter(
            self,
            "VapidPrivateKey",
            type="String",
            default="",
            no_echo=True,
            description="Clave privada VAPID (scripts/generar_claves_vapid.py). Vacío = push deshabilitado.",
        )
        vapid_subject = CfnParameter(
            self,
            "VapidSubject",
            type="String",
            default="mailto:telos@example.com",
            description="Contacto (mailto: o https:) que exige el protocolo VAPID/Web Push.",
        )
        # Comparte el mismo secreto entre la API y el Scheduler de Fase 4
        # más abajo (ver events.Connection) -- protege
        # /api/push/enviar-recordatorios de ser invocado por cualquiera
        # que adivine la URL, ya que ese endpoint no pide sesión de
        # Cognito (lo llama el Scheduler, no una persona).
        push_scheduler_secret = CfnParameter(
            self,
            "PushSchedulerSecret",
            type="String",
            no_echo=True,
            description=(
                "Secreto compartido entre EventBridge Scheduler y "
                "/api/push/enviar-recordatorios -- generá uno random "
                "vos mismo (ej. `openssl rand -hex 32`), no tiene default."
            ),
        )

        imagen_api = ecr_assets.DockerImageAsset(
            self,
            "ImagenApi",
            directory=str(_REPO_ROOT),
            file="api/Dockerfile",
            exclude=[".venv", ".git", "infra", "data", "ui/app.py", "**/__pycache__", "*.md"],
        )
        imagen_api.repository.grant_pull(rol_agentes)

        imagen_web = ecr_assets.DockerImageAsset(
            self,
            "ImagenWeb",
            # Contexto propio (web/), no la raíz del repo: a diferencia
            # de ui/ y api/, el frontend Next.js no importa nada de
            # agents/tools -- es un proyecto Node autocontenido que solo
            # habla con la API por HTTP.
            directory=str(_REPO_ROOT / "web"),
            exclude=["node_modules", ".next", ".git"],
        )
        imagen_web.repository.grant_pull(rol_agentes)

        sg_instancia_web = ec2.SecurityGroup(
            self,
            "SgInstanciaWeb",
            vpc=vpc,
            description="Permite trafico HTTP entrante a la API (8000) y a Next.js (3000).",
            allow_all_outbound=True,
        )
        sg_instancia_web.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(8000), "API FastAPI (via CloudFront)")
        sg_instancia_web.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(3000), "Next.js (via CloudFront)")

        comandos_usuario_web = ec2.UserData.for_linux()
        comandos_usuario_web.add_commands(
            "dnf install -y docker",
            "systemctl enable --now docker",
            f"aws ecr get-login-password --region {self.region} | "
            f"docker login --username AWS --password-stdin {self.account}.dkr.ecr.{self.region}.amazonaws.com",
            "docker run -d --restart unless-stopped --network host "
            f'-e TELOS_AWS_REGION="{self.region}" '
            '-e TELOS_FICHA_BACKEND="agentcore" '
            '-e TELOS_REQUIRE_LOGIN="1" '
            f'-e COGNITO_DOMAIN="{user_pool_domain.base_url()}" '
            f'-e COGNITO_USER_POOL_ID="{user_pool.user_pool_id}" '
            f'-e COGNITO_CLIENT_ID="{user_pool_client.user_pool_client_id}" '
            f'-e COGNITO_CLIENT_SECRET="{user_pool_client.user_pool_client_secret.unsafe_unwrap()}" '
            f'-e APP_URL="{web_url.value_as_string}/api/auth/callback" '
            f'-e LOGOUT_REDIRECT_URL="{web_url.value_as_string}" '
            f'-e VAPID_PUBLIC_KEY="{vapid_public_key.value_as_string}" '
            f'-e VAPID_PRIVATE_KEY="{vapid_private_key.value_as_string}" '
            f'-e VAPID_SUBJECT="{vapid_subject.value_as_string}" '
            f'-e PUSH_SCHEDULER_SECRET="{push_scheduler_secret.value_as_string}" '
            f"{imagen_api.image_uri}",
            # --network host también acá: Next.js necesita pegarle a la
            # API por localhost:8000 (ver web/src/lib/api.ts).
            "docker run -d --restart unless-stopped --network host "
            f'-e API_INTERNAL_URL="http://localhost:8000" '
            f"{imagen_web.image_uri}",
        )

        instancia_web = ec2.Instance(
            self,
            "InstanciaWeb",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            security_group=sg_instancia_web,
            role=rol_agentes,
            user_data=comandos_usuario_web,
            user_data_causes_replacement=True,
            associate_public_ip_address=True,
        )

        distribucion_web = cloudfront.Distribution(
            self,
            "DistribucionWeb",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    instancia_web.instance_public_dns_name,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    http_port=3000,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        instancia_web.instance_public_dns_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                        http_port=8000,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    # ALL_VIEWER (no solo headers): la cookie de sesión
                    # (api/auth.py) y el query string ?code=/&state= del
                    # callback de Cognito tienen que llegar intactos al
                    # origen, mismo motivo que DistribucionUI.
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                )
            },
        )

        CfnOutput(
            self,
            "UrlServicioWeb",
            value=f"https://{distribucion_web.distribution_domain_name}",
            description=(
                "Pasar como --parameters WebUrl=<esta URL> en un segundo "
                "deploy. Probar con GET /api/salud."
            ),
        )
        CfnOutput(
            self,
            "IdInstanciaWeb",
            value=instancia_web.instance_id,
            description=(
                "Usar con `aws ssm start-session --target <esto>` para "
                "entrar a la instancia de la API/Next.js si el user data falla."
            ),
        )

        # --- Fase 4 (rama gamificacion): recordatorios automáticos.
        # Una EventBridge Rule programada dispara un POST diario a
        # /api/push/enviar-recordatorios en vez de un runtime Lambda
        # aparte -- reutiliza el mismo FastAPI ya desplegado, sin
        # duplicar la lógica de "quién está suscripto" en dos lugares
        # (ver plan de migración sección C, punto 8). Autenticado con un
        # secreto compartido (api/auth.py::verificar_secreto_scheduler),
        # no con Cognito: quien llama es la Rule, no una persona.
        #
        # NO usa AWS::Scheduler::Schedule (el servicio "EventBridge
        # Scheduler" nuevo, separado de EventBridge clásico): un deploy
        # real contra la cuenta tiró "Provided Arn is not in correct
        # format" al pasarle el ARN de un API destination como target de
        # Scheduler -- Scheduler no soporta API destinations como target
        # directo (a diferencia de lo que sugiere su propia doc de
        # "universal targets"). events.Rule + events_targets.ApiDestination
        # es el patrón real y soportado para "algo programado que llama a
        # un endpoint HTTPS externo" -- crea y adjunta el rol IAM solo,
        # sin necesitar un iam.Role a mano como el Schedule sí pedía.
        conexion_scheduler_push = events.Connection(
            self,
            "ConexionSchedulerPush",
            authorization=events.Authorization.api_key(
                "X-Telos-Scheduler-Secret",
                SecretValue.unsafe_plain_text(push_scheduler_secret.value_as_string),
            ),
            description="Credencial que EventBridge adjunta al llamar a /api/push/enviar-recordatorios.",
        )

        destino_recordatorios_push = events.ApiDestination(
            self,
            "DestinoRecordatoriosPush",
            connection=conexion_scheduler_push,
            endpoint=f"https://{distribucion_web.distribution_domain_name}/api/push/enviar-recordatorios",
            http_method=events.HttpMethod.POST,
            rate_limit_per_second=1,
        )

        events.Rule(
            self,
            "ReglaRecordatoriosPush",
            description="Recordatorio diario de Telos vía Web Push (Fase 4 del plan de migración).",
            # Una vez por día alcanza para el MVP -- el spec prohíbe el
            # tono de hábito-shaming en Fase 5 (ver
            # agents/seguimiento.py), así que esto es deliberadamente
            # infrecuente, no un empujón constante.
            schedule=events.Schedule.rate(Duration.days(1)),
            targets=[events_targets.ApiDestination(destino_recordatorios_push)],
        )
