"""
Kubernetes implementation of InfraController — PLACEHOLDER for future use.
This file provides the interface structure but is not yet implemented.
"""

from app.services.infra_controller import ActionResult, InfraController, ServiceStatus


class KubernetesController(InfraController):
    """
    Kubernetes-based implementation of InfraController.
    Will use the kubernetes Python client to manage deployments.
    NOT YET IMPLEMENTED — placeholder for future migration from Docker.
    """

    def __init__(self, namespace: str = "default") -> None:
        self._namespace = namespace
        raise NotImplementedError(
            "KubernetesController is a placeholder. "
            "Use DockerController for the current Docker-based setup."
        )

    def restart_service(self, service_name: str) -> ActionResult:
        raise NotImplementedError("KubernetesController.restart_service not implemented")

    def scale_service(self, service_name: str, replicas: int) -> ActionResult:
        raise NotImplementedError("KubernetesController.scale_service not implemented")

    def get_status(self, service_name: str) -> ServiceStatus:
        raise NotImplementedError("KubernetesController.get_status not implemented")

    def get_all_statuses(self) -> list[ServiceStatus]:
        raise NotImplementedError("KubernetesController.get_all_statuses not implemented")