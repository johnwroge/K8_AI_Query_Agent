"""
Kubernetes client module for gathering cluster information.
Handles all interactions with the Kubernetes API.
"""
import logging
from typing import Dict, List, Any, Optional
from kubernetes import client as k8s_client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class K8sClient:
    """Client for interacting with Kubernetes cluster."""
    
    def __init__(self):
        self.v1: Optional[k8s_client.CoreV1Api] = None
        self.apps_v1: Optional[k8s_client.AppsV1Api] = None
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
            self.apps_v1 = k8s_client.AppsV1Api()
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    def get_namespaces(self, filter_pattern: Optional[str] = None) -> List[str]:
        """
        Get list of namespaces, optionally filtered by pattern.
        
        Args:
            filter_pattern: Optional string to filter namespace names
            
        Returns:
            List of namespace names
        """
        try:
            namespaces = self.v1.list_namespace()
            all_namespaces = [ns.metadata.name for ns in namespaces.items]
            
            if filter_pattern:
                return [ns for ns in all_namespaces if filter_pattern in ns]
            
            return all_namespaces
            
        except ApiException as e:
            logger.error(f"Error fetching namespaces: {e}")
            return []
    
    def get_pods(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Get detailed information about pods in a namespace.
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            List of pod information dictionaries
        """
        try:
            pods = self.v1.list_namespaced_pod(namespace)
            return [self._extract_pod_info(pod) for pod in pods.items]
            
        except ApiException as e:
            logger.error(f"Error fetching pods in namespace {namespace}: {e}")
            return []
    
    def get_services(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """
        Get service information for a namespace.
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            List of service information dictionaries
        """
        try:
            services = self.v1.list_namespaced_service(namespace)
            return [self._extract_service_info(svc) for svc in services.items]
            
        except ApiException as e:
            logger.error(f"Error fetching services in namespace {namespace}: {e}")
            return []
    
    def get_secrets(self, namespace: str = "default") -> List[Dict[str, str]]:
        """Get secret names in a namespace (not their values)."""
        try:
            secrets = self.v1.list_namespaced_secret(namespace)
            return [
                {
                    "name": secret.metadata.name,
                    "namespace": secret.metadata.namespace,
                    "type": secret.type
                }
                for secret in secrets.items
            ]
        except ApiException as e:
            logger.error(f"Error fetching secrets in namespace {namespace}: {e}")
            return []
    
    def get_configmaps(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """Get configmap information in a namespace."""
        try:
            configmaps = self.v1.list_namespaced_config_map(namespace)
            return [
                {
                    "name": cm.metadata.name,
                    "namespace": cm.metadata.namespace,
                    "data_keys": list(cm.data.keys()) if cm.data else []
                }
                for cm in configmaps.items
            ]
        except ApiException as e:
            logger.error(f"Error fetching configmaps in namespace {namespace}: {e}")
            return []
    
    def get_deployments(self, namespace: str = "default") -> List[Dict[str, Any]]:
        """Get deployment information in a namespace."""
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
            return [
                {
                    "name": dep.metadata.name,
                    "namespace": dep.metadata.namespace,
                    "replicas": dep.spec.replicas,
                    "available_replicas": dep.status.available_replicas or 0
                }
                for dep in deployments.items
            ]
        except ApiException as e:
            logger.error(f"Error fetching deployments in namespace {namespace}: {e}")
            return []
    
    def _extract_pod_info(self, pod) -> Dict[str, Any]:
        """Extract relevant information from a pod object."""
        pod_info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name,
            "containers": []
        }
        
        if pod.spec.containers:
            for container in pod.spec.containers:
                container_info = {
                    "name": container.name,
                    "image": container.image,
                    "ports": []
                }
                
                if container.ports:
                    container_info["ports"] = [
                        {
                            "container_port": p.container_port,
                            "protocol": p.protocol
                        }
                        for p in container.ports
                    ]
                
                pod_info["containers"].append(container_info)
        
        return pod_info
    
    def _extract_service_info(self, service) -> Dict[str, Any]:
        """Extract relevant information from a service object."""
        service_info = {
            "name": service.metadata.name,
            "namespace": service.metadata.namespace,
            "type": service.spec.type,
            "cluster_ip": service.spec.cluster_ip,
            "ports": []
        }
        
        if service.spec.ports:
            service_info["ports"] = [
                {
                    "port": port.port,
                    "target_port": str(port.target_port),
                    "protocol": port.protocol,
                    "name": port.name
                }
                for port in service.spec.ports
            ]
        
        return service_info
    
    def get_cluster_summary(self, namespaces: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get a comprehensive summary of cluster resources.
        
        Args:
            namespaces: List of namespaces to query. If None, uses 'default'
            
        Returns:
            Dictionary with pods, services, secrets, configmaps, and deployments
        """
        if namespaces is None:
            namespaces = ["default"]
        
        summary = {
            "pods": [],
            "services": [],
            "secrets": [],
            "configmaps": [],
            "deployments": []
        }
        
        for namespace in namespaces:
            logger.debug(f"Gathering resources from namespace: {namespace}")
            summary["pods"].extend(self.get_pods(namespace))
            summary["services"].extend(self.get_services(namespace))
            summary["secrets"].extend(self.get_secrets(namespace))
            summary["configmaps"].extend(self.get_configmaps(namespace))
            summary["deployments"].extend(self.get_deployments(namespace))
        
        logger.info(
            f"Cluster summary: {len(summary['pods'])} pods, "
            f"{len(summary['services'])} services, "
            f"{len(summary['deployments'])} deployments"
        )
        
        return summary