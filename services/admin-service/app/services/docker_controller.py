import logging
from typing import Optional

import docker
from docker.errors import NotFound, APIError

from app.services.infra_controller import ActionResult, InfraController, ServiceStatus

logger = logging.getLogger("docker_controller")

# Map logical service names to Docker container names
CONTAINER_NAME_MAP = {
    "service-a": "service-a",
    "service-b": "service-b",
    "service-c": "service-c",
    "admin-service": "admin-service",
}


class DockerController(InfraController):
    """
    Docker-based implementation of InfraController.
    Uses the Docker SDK to manage containers.
    """

    def __init__(self) -> None:
        try:
            self._client = docker.from_env()
            logger.info("DockerController initialized — connected to Docker daemon")
        except Exception as exc:
            logger.error(f"Failed to connect to Docker daemon: {exc}")
            self._client = None

    def _get_container_name(self, service_name: str) -> str:
        return CONTAINER_NAME_MAP.get(service_name, service_name)

    def _get_container(self, service_name: str):
        if self._client is None:
            return None
        container_name = self._get_container_name(service_name)
        try:
            return self._client.containers.get(container_name)
        except NotFound:
            logger.warning(f"Container '{container_name}' not found")
            return None
        except APIError as exc:
            logger.error(f"Docker API error for '{container_name}': {exc}")
            return None

    def restart_service(self, service_name: str) -> ActionResult:
        container = self._get_container(service_name)
        if container is None:
            return ActionResult(
                success=False,
                service_name=service_name,
                action="restart",
                message=f"Container for {service_name} not found",
            )

        try:
            container.restart(timeout=10)
            logger.info(f"Container '{service_name}' restarted successfully")
            return ActionResult(
                success=True,
                service_name=service_name,
                action="restart",
                message=f"{service_name} restarted successfully",
                details=f"Container ID: {container.short_id}",
            )
        except APIError as exc:
            logger.error(f"Failed to restart '{service_name}': {exc}")
            return ActionResult(
                success=False,
                service_name=service_name,
                action="restart",
                message=f"Failed to restart {service_name}: {exc}",
            )

    def stop_service(self, service_name: str) -> ActionResult:
        """Stop a Docker container (simulate service down)."""
        container = self._get_container(service_name)
        if container is None:
            return ActionResult(
                success=False,
                service_name=service_name,
                action="stop",
                message=f"Container for {service_name} not found",
            )

        try:
            container.stop(timeout=5)
            logger.info(f"Container '{service_name}' stopped successfully")
            return ActionResult(
                success=True,
                service_name=service_name,
                action="stop",
                message=f"{service_name} stopped successfully",
                details=f"Container ID: {container.short_id}",
            )
        except APIError as exc:
            logger.error(f"Failed to stop '{service_name}': {exc}")
            return ActionResult(
                success=False,
                service_name=service_name,
                action="stop",
                message=f"Failed to stop {service_name}: {exc}",
            )
    def scale_service(self, service_name: str, replicas: int) -> ActionResult:
        """
        Scale a service dynamically using the Docker SDK.
        This actually spins up new containers and attaches them to the network
        with the correct alias, mimicking Swarm/Compose native scaling without
        breaking the local compose project structure!
        """
        container = self._get_container(service_name)
        if container is None:
            return ActionResult(
                success=False,
                service_name=service_name,
                action="scale",
                message=f"Container for {service_name} not found",
            )

        try:
            # Gather config from the main container
            image_name = container.image.tags[0] if container.image.tags else container.image.id
            env_vars = container.attrs['Config']['Env']
            
            networks = container.attrs['NetworkSettings']['Networks']
            network_name = list(networks.keys())[0] if networks else "bridge"
            network = self._client.networks.get(network_name)

            # Aggressively clean up dead/exited replicas first
            all_replicas = self._client.containers.list(
                all=True, filters={"label": f"scaled_for={service_name}"}
            )
            running_replicas = []
            for c in all_replicas:
                if c.status == "running":
                    running_replicas.append(c)
                else:
                    try:
                        c.remove(force=True)
                    except Exception:
                        pass
                        
            current_count = 1 + len(running_replicas)

            if replicas > current_count:
                # Scale up
                for i in range(current_count, replicas):
                    replica_name = f"{service_name}-replica-{i}"
                    
                    # Clean up old dead replicas if any
                    try:
                        old = self._client.containers.get(replica_name)
                        old.remove(force=True)
                    except docker.errors.NotFound:
                        pass
                        
                    new_c = self._client.containers.run(
                        image=image_name,
                        name=replica_name,
                        detach=True,
                        environment=env_vars,
                        labels={"scaled_for": service_name}
                    )
                    # Connect to the network with the primary service's alias! 
                    # This tells Docker's internal DNS to round-robin traffic.
                    network.connect(new_c, aliases=[service_name])
                    logger.info(f"Spawned native replica: {replica_name}")
                    
            elif replicas < current_count:
                # Scale down
                for i in range(replicas, current_count):
                    try:
                        c = self._client.containers.get(f"{service_name}-replica-{i}")
                        c.remove(force=True)
                        logger.info(f"Removed native replica: {service_name}-replica-{i}")
                    except docker.errors.NotFound:
                        continue
                        
            return ActionResult(
                success=True,
                service_name=service_name,
                action="scale",
                message=f"{service_name} scaled to {replicas} replicas natively",
                details=f"Dynamically spawned {replicas-1} physical Docker replica instances on {network_name}.",
            )
        except Exception as exc:
            logger.error(f"Failed to scale '{service_name}': {exc}")
            return ActionResult(
                success=False,
                service_name=service_name,
                action="scale",
                message=f"Failed to scale {service_name}: {exc}",
            )

    def get_status(self, service_name: str) -> ServiceStatus:
        container = self._get_container(service_name)
        if container is None:
            return ServiceStatus(
                service_name=service_name,
                status="stopped",
                replicas=0,
                details="Container not found",
            )

        try:
            container.reload()
            state = container.status
            running_replicas = 1 if state == "running" else 0
            
            # Add dynamic replicas
            existing = self._client.containers.list(filters={"label": f"scaled_for={service_name}"})
            running_replicas += sum(1 for c in existing if c.status == "running")
            total_replicas = 1 + len(existing)
            
            return ServiceStatus(
                service_name=service_name,
                status=state if state != "running" else ("running" if running_replicas > 0 else "stopped"),
                replicas=running_replicas,
                details=f"Main ID: {container.short_id}, Total Instances: {total_replicas} ({running_replicas} running)",
            )
        except Exception as exc:
            return ServiceStatus(
                service_name=service_name,
                status="unknown",
                replicas=0,
                details=str(exc),
            )

    def get_all_statuses(self) -> list[ServiceStatus]:
        statuses = []
        for service_name in CONTAINER_NAME_MAP:
            statuses.append(self.get_status(service_name))
        return statuses