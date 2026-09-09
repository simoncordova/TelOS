"""Stack de CDK para Telos. Ver Paso 4 del plan de implementación.

Cubre solo lo "clásico": IAM, build/push de la imagen de la UI, y
hosting en App Runner. Deliberadamente NO define recursos
AWS::BedrockAgentCore::* — Runtime/Memory/Gateway se configuran aparte
con `agentcore configure` / `agentcore launch` desde CloudShell,
reutilizando el rol IAM que este stack deja creado (ver output
ArnRolAgentes). Documentado en el README como dos pasos de deploy
separados, no uno solo.
"""

from pathlib import Path

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_apprunner as apprunner
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_iam as iam
from constructs import Construct

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TelosStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
                # Acciones de AgentCore Memory/Gateway: servicio nuevo,
                # confirmar nombres exactos de acción contra la
                # documentación vigente antes de endurecer a least
                # privilege. Wildcard de servicio aceptable para el MVP.
                actions=["bedrock-agentcore:*"],
                resources=["*"],
            )
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
