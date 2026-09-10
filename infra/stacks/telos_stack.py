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
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_iam as iam
from constructs import Construct

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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
        rol_agentes.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=["*"],
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

        # --- Autenticación: Cognito con usuarios propios ---
        app_url = CfnParameter(
            self,
            "AppUrl",
            type="String",
            default="https://localhost:8501",
            description=(
                "URL pública de la UI. El primer deploy no la conoce "
                "todavía (App Runner la genera recién al crearse) — deja "
                "el default, y hacé un segundo deploy pasando "
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

        servicio_ui = apprunner.CfnService(
            self,
            "ServicioStreamlit",
            service_name="telos-ui",
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
