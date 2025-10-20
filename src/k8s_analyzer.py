"""
Kubernetes analyzer module for debugging crashed pods.
Gathers comprehensive diagnostic data from the cluster.
"""
import logging
from typing import Dict, List, Any, Optional
from kubernetes import client as k8s_client, config
from kubernetes.client.rest import ApiException
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class K8sAnalyzer:
    """Analyzer for gathering detailed Kubernetes debugging information."""
    
    def __init__(self):
        self.v1: Optional[k8s_client.CoreV1Api] = None
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Kubernetes client configuration."""
        try:
            import os
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            else:
                config.load_kube_config()
                logger.info("Loaded local Kubernetes configuration")
            
            self.v1 = k8s_client.CoreV1Api()
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes analyzer: {e}")
            raise
    
    def get_pod_details(self, pod_name: str, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get comprehensive pod details including status, configuration, and restart count.
        
        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with pod details or None if not found
        """
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            
            # Extract container statuses
            container_statuses = []
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    status_info = {
                        "name": cs.name,
                        "ready": cs.ready,
                        "restart_count": cs.restart_count,
                        "image": cs.image,
                        "state": self._extract_container_state(cs.state),
                        "last_state": self._extract_container_state(cs.last_state) if cs.last_state else None
                    }
                    container_statuses.append(status_info)
            
            # Extract environment variables (without sensitive values)
            env_vars = []
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.env:
                        for env in container.env:
                            env_info = {
                                "name": env.name,
                                "value": env.value if env.value else "[from secret/configmap]"
                            }
                            env_vars.append(env_info)
            
            # Extract resource requests/limits
            resources = {}
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.resources:
                        resources[container.name] = {
                            "requests": dict(container.resources.requests) if container.resources.requests else {},
                            "limits": dict(container.resources.limits) if container.resources.limits else {}
                        }
            
            pod_details = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "phase": pod.status.phase,
                "node": pod.spec.node_name,
                "created_at": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None,
                "container_statuses": container_statuses,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message
                    }
                    for c in (pod.status.conditions or [])
                ],
                "environment": env_vars,
                "resources": resources,
                "restart_policy": pod.spec.restart_policy
            }
            
            return pod_details
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod {pod_name} not found in namespace {namespace}")
                return None
            logger.error(f"Error fetching pod details: {e}")
            raise
    
    def _extract_container_state(self, state) -> Dict[str, Any]:
        """Extract information from container state object."""
        if state.running:
            return {
                "status": "running",
                "started_at": state.running.started_at.isoformat() if state.running.started_at else None
            }
        elif state.waiting:
            return {
                "status": "waiting",
                "reason": state.waiting.reason,
                "message": state.waiting.message
            }
        elif state.terminated:
            return {
                "status": "terminated",
                "exit_code": state.terminated.exit_code,
                "reason": state.terminated.reason,
                "message": state.terminated.message,
                "started_at": state.terminated.started_at.isoformat() if state.terminated.started_at else None,
                "finished_at": state.terminated.finished_at.isoformat() if state.terminated.finished_at else None
            }
        return {"status": "unknown"}
    
    def get_pod_logs(
        self, 
        pod_name: str, 
        namespace: str = "default",
        lines: int = 100,
        container: Optional[str] = None,
        previous: bool = False
    ) -> str:
        """
        Get recent logs from a pod.
        
        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            lines: Number of log lines to retrieve (default 100)
            container: Specific container name (optional)
            previous: Get logs from previous container instance (useful for crashes)
            
        Returns:
            Log text or error message
        """
        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=lines,
                previous=previous
            )
            return logs
            
        except ApiException as e:
            if e.status == 404:
                return f"Pod or container not found"
            elif e.status == 400 and previous:
                return "No previous container instance available"
            logger.error(f"Error fetching pod logs: {e}")
            return f"Error fetching logs: {e.reason}"
    
    def get_pod_events(
        self, 
        pod_name: str, 
        namespace: str = "default",
        minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent events related to a pod.
        
        Args:
            pod_name: Name of the pod
            namespace: Kubernetes namespace
            minutes: How many minutes back to look for events
            
        Returns:
            List of event dictionaries
        """
        try:
            events = self.v1.list_namespaced_event(namespace=namespace)
            
            # Filter events for this pod
            pod_events = []
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            for event in events.items:
                # Check if event is related to our pod
                if (event.involved_object.name == pod_name and 
                    event.involved_object.kind == "Pod"):
                    
                    # Check if event is recent enough
                    event_time = event.last_timestamp or event.first_timestamp
                    if event_time and event_time.replace(tzinfo=None) > cutoff_time:
                        pod_events.append({
                            "timestamp": event_time.isoformat() if event_time else None,
                            "type": event.type,
                            "reason": event.reason,
                            "message": event.message,
                            "count": event.count,
                            "source": event.source.component if event.source else None
                        })
            
            # Sort by timestamp (newest first)
            pod_events.sort(key=lambda x: x["timestamp"] or "", reverse=True)
            
            return pod_events
            
        except ApiException as e:
            logger.error(f"Error fetching pod events: {e}")
            return []
    
    def analyze_pod(
        self, 
        pod_name: str, 
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a pod, gathering all relevant debugging data.
        
        Args:
            pod_name: Name of the pod to analyze
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary with all debugging information
        """
        logger.info(f"Analyzing pod {pod_name} in namespace {namespace}")
        
        # Gather all data
        pod_details = self.get_pod_details(pod_name, namespace)
        
        if not pod_details:
            return {
                "error": f"Pod '{pod_name}' not found in namespace '{namespace}'",
                "exists": False
            }
        
        # Get logs from current and previous container if crashed
        current_logs = ""
        previous_logs = ""
        
        if pod_details["container_statuses"]:
            # Try to get logs from first container
            container_name = pod_details["container_statuses"][0]["name"]
            current_logs = self.get_pod_logs(pod_name, namespace, container=container_name)
            
            # If container has restarted, get previous logs
            if pod_details["container_statuses"][0]["restart_count"] > 0:
                previous_logs = self.get_pod_logs(
                    pod_name, 
                    namespace, 
                    container=container_name,
                    previous=True
                )
        
        events = self.get_pod_events(pod_name, namespace)
        
        analysis_data = {
            "exists": True,
            "pod_details": pod_details,
            "current_logs": current_logs,
            "previous_logs": previous_logs,
            "events": events,
            "analyzed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Analysis complete for {pod_name}")
        return analysis_data