"""Stack de CDK para Telos. Ver Paso 4 del plan de implementación.

Cubre lo "clásico": IAM, build/push de la imagen de la UI, hosting en App
Runner, y autenticación (Cognito, usuarios propios). Deliberadamente NO
define recursos AWS::BedrockAgentCore::* — Runtime/Memory/Gateway se
configuran aparte con `agentcore configure` / `agentcore launch` desde
CloudShell, reutilizando el rol IAM que este stack deja creado (ver
output ArnRolAgentes). Documentado en el README como dos pasos de deploy
separados, no uno solo.

Autenticación: Cognito con su propio User Pool (self_sign_up_enabled=
False -- no hay registro público, el dueño de la cuenta crea los
usuarios de prueba a mano con `aws cognito-idp admin-create-user`, ver
README). Sin proveedores externos (nada de Google/Facebook/etc.) a
propósito: evita cualquier dependencia con una cuenta de terceros.
Requiere un SEGUNDO deploy igual: el callback URL de Cognito tiene que
ser la URL real de App Runner, que solo se conoce después del primer
deploy (App Runner la genera). Ver el parámetro AppUrl más abajo.
"""

from pathlib import Path

from aws_cdk import CfnOutput, CfnParameter, RemovalPolicy, Stack, Tags
from aws_cdk import aws_apprunner as apprunner
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ecr_assets as ecr_assets
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

        # Rol que ejecuta el código de agentes. En el MVP corre dentro del
        # mismo contenedor de Streamlit (App Runner instance role); si más
        # adelante se despliega el Runtime de AgentCore por separado, este
        # mismo rol se puede pasar como execution role de `agentcore
        # launch` en vez de crear uno nuevo.
        rol_agentes = iam.Role(
            self,
            "RolEjecucionAgentes",
            assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
            description=(
                "Permisos para invocar Bedrock y AgentCore Memory/Gateway "
                "desde el código de agentes de Telos."
            ),
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
                "todavía (App Runner la genera recién al crearse) — deja "
                "el default, y haz un segundo deploy pasando "
                "--parameters AppUrl=<el output UrlServicioUI del primer "
                "deploy> para que el login funcione de verdad."
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
                callback_urls=[app_url.value_as_string],
                logout_urls=[app_url.value_as_string],
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
            exclude=[".venv", ".git", "infra", "data", "**/__pycache__", "*.md"],
        )

        rol_acceso_ecr = iam.Role(
            self,
            "RolAccesoECR",
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
        )
        imagen_ui.repository.grant_pull(rol_acceso_ecr)

        # Tope de blast radius: nunca más de 1 instancia, pase lo que
        # pase con el tráfico (malicioso o no) -- alcanza de sobra para
        # los 3 usuarios de prueba del demo, y evita que App Runner
        # escale de más (hasta 25 por default) ante tráfico anómalo.
        escalado_ui = apprunner.CfnAutoScalingConfiguration(
            self,
            "EscaladoUI",
            auto_scaling_configuration_name="telos-ui-tope-1",
            min_size=1,
            max_size=1,
        )

        servicio_ui = apprunner.CfnService(
            self,
            "ServicioStreamlit",
            service_name="telos-ui",
            auto_scaling_configuration_arn=escalado_ui.attr_auto_scaling_configuration_arn,
            source_configuration=apprunner.CfnService.SourceConfigurationProperty(
                auto_deployments_enabled=False,
                authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                    access_role_arn=rol_acceso_ecr.role_arn,
                ),
                image_repository=apprunner.CfnService.ImageRepositoryProperty(
                    image_identifier=imagen_ui.image_uri,
                    image_repository_type="ECR",
                    image_configuration=apprunner.CfnService.ImageConfigurationProperty(
                        port="8501",
                        runtime_environment_variables=[
                            apprunner.CfnService.KeyValuePairProperty(
                                name="TELOS_AWS_REGION",
                                value=self.region,
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                # Sin esto, el contenedor desplegado usa el
                                # backend JSON local por defecto -- efímero,
                                # se pierde en cada restart/redeploy. Es
                                # justo lo que la persistencia P0 (ficha
                                # versionada) tiene que evitar.
                                name="TELOS_FICHA_BACKEND",
                                value="agentcore",
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="COGNITO_DOMAIN",
                                value=user_pool_domain.base_url(),
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="COGNITO_USER_POOL_ID",
                                value=user_pool.user_pool_id,
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="COGNITO_CLIENT_ID",
                                value=user_pool_client.user_pool_client_id,
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                # TODO endurecer: mover a Secrets Manager +
                                # runtime_environment_secrets en vez de
                                # variable en texto plano. Aceptable para
                                # el MVP del hackathon (no queda pública,
                                # solo visible en la consola de App Runner
                                # dentro de la cuenta).
                                name="COGNITO_CLIENT_SECRET",
                                value=user_pool_client.user_pool_client_secret.unsafe_unwrap(),
                            ),
                            apprunner.CfnService.KeyValuePairProperty(
                                name="APP_URL",
                                value=app_url.value_as_string,
                            ),
                        ],
                    ),
                ),
            ),
            instance_configuration=apprunner.CfnService.InstanceConfigurationProperty(
                cpu="1024",
                memory="2048",
                instance_role_arn=rol_agentes.role_arn,
            ),
        )

        CfnOutput(
            self,
            "UrlServicioUI",
            value=f"https://{servicio_ui.attr_service_url}",
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
