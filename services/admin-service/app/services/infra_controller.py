from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServiceStatus:
    service_name: str
    status: str  # "running", "stopped", "restarting", "unknown"
    replicas: int
    details: Optional[str] = None


@dataclass
class ActionResult:
    success: bool
    service_name: str
    action: str  # "restart", "scale"
    message: str
    details: Optional[str] = None


class InfraController(ABC):
    """
    Abstract interface for infrastructure operations.
    All Docker/Kubernetes commands MUST go through this layer.
    """

    @abstractmethod
    def restart_service(self, service_name: str) -> ActionResult:
        """Restart a service by name."""
        ...

    @abstractmethod
    def scale_service(self, service_name: str, replicas: int) -> ActionResult:
        """Scale a service to the given number of replicas."""
        ...

    @abstractmethod
    def get_status(self, service_name: str) -> ServiceStatus:
        """Get the current status of a service."""
        ...

    @abstractmethod
    def get_all_statuses(self) -> list[ServiceStatus]:
        """Get status of all managed services."""
        ...
