import json
import logging
import os
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
from kubernetes import client as k8s_client, config
from openai import OpenAI
from typing import List, Dict, Any
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
import time

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s - %(message)s',
    filename='agent.log', 
    filemode='a'
)
logging.getLogger().addHandler(logging.StreamHandler())

QUERY_COUNTER = Counter('k8s_agent_queries_total', 'Total number of queries processed')
QUERY_LATENCY = Histogram('k8s_agent_query_duration_seconds', 'Time spent processing queries')
ERROR_COUNTER = Counter('k8s_agent_errors_total', 'Total number of errors', ['error_type'])
CLUSTER_INFO = Info('k8s_agent_cluster', 'Kubernetes cluster information')

class K8sAssistant:
    def __init__(self):
        self.openai_client = OpenAI()
        self.v1 = None
        self.apps_v1 = None
        self.initialize_k8s()
        self.initialize_openai()

    def initialize_k8s(self):
        """Initialize Kubernetes client"""
        try:
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                config.load_incluster_config()
            else:
                config.load_kube_config()
            
            self.v1 = k8s_client.CoreV1Api()
            self.apps_v1 = k8s_client.AppsV1Api()
            logging.info("Successfully connected to Kubernetes cluster")
        except Exception as e:
            logging.error(f"Failed to connect to Kubernetes cluster: {e}")
            raise

    def initialize_openai(self):
        """Test OpenAI connection"""
        logging.info("Testing OpenAI connection...")
        try:
            test_response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Say hello"}],
                temperature=0
            )
            logging.info("OpenAI connection successful")
        except Exception as e:
            logging.error(f"OpenAI error: {e}")
            raise

    def get_k8s_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """Gather detailed information about the Kubernetes cluster with focus on Harbor components"""
        info = {}
        try:
            logging.debug("Starting Kubernetes information gathering...")
            logging.debug(f"Current context: {config.list_kube_config_contexts()[0]}")
            
            namespaces = self.v1.list_namespace()
            all_namespaces = [ns.metadata.name for ns in namespaces.items]
            logging.debug(f"Available namespaces: {all_namespaces}")
            
            harbor_namespaces = [ns for ns in all_namespaces if 'harbor' in ns]
            logging.debug(f"Detected Harbor namespaces: {harbor_namespaces}")
            
            if not harbor_namespaces:
                logging.warning("No Harbor namespaces found. Checking default namespace as fallback...")
                harbor_namespaces = ['default'] 

            all_pods = []
            all_services = []
            all_secrets = []
            all_configmaps = []

            for ns in harbor_namespaces:
                try:
                    logging.debug(f"Processing namespace: {ns}")
                    
                    try:
                        pods = self.v1.list_namespaced_pod(ns)
                        pod_names = [p.metadata.name for p in pods.items]
                        logging.debug(f"Found pods in {ns}: {pod_names}")
                    except Exception as pod_error:
                        logging.error(f"Error getting pods in namespace {ns}: {pod_error}")
                        continue

                    try:
                        services = self.v1.list_namespaced_service(ns)
                        service_names = [s.metadata.name for s in services.items]
                        logging.debug(f"Found services in {ns}: {service_names}")
                    except Exception as svc_error:
                        logging.error(f"Error getting services in namespace {ns}: {svc_error}")
                        continue

                    try:
                        secrets = self.v1.list_namespaced_secret(ns)
                        secret_names = [s.metadata.name for s in secrets.items]
                        logging.debug(f"Found secrets in {ns}: {secret_names}")
                    except Exception as secret_error:
                        logging.error(f"Error getting secrets in namespace {ns}: {secret_error}")
                        continue

                    try:
                        configmaps = self.v1.list_namespaced_config_map(ns)
                        configmap_names = [cm.metadata.name for cm in configmaps.items]
                        logging.debug(f"Found configmaps in {ns}: {configmap_names}")
                    except Exception as cm_error:
                        logging.error(f"Error getting configmaps in namespace {ns}: {cm_error}")
                        continue

                    for pod in pods.items:
                        try:
                            pod_info = {
                                "name": pod.metadata.name,
                                "namespace": pod.metadata.namespace,
                                "status": pod.status.phase,
                                "containers": []
                            }
                            
                            for container in pod.spec.containers:
                                container_info = self._get_container_info(container)
                                pod_info["containers"].append(container_info)
                            
                            if pod.spec.volumes:
                                pod_info["volumes"] = self._get_volume_info(pod.spec.volumes)
                            
                            all_pods.append(pod_info)
                            
                        except Exception as pod_process_error:
                            logging.error(f"Error processing pod {pod.metadata.name}: {pod_process_error}")
                            continue

                    for svc in services.items:
                        try:
                            service_info = {
                                "name": svc.metadata.name,
                                "namespace": svc.metadata.namespace,
                                "ports": [
                                    {
                                        "port": port.port,
                                        "target_port": port.target_port,
                                        "protocol": port.protocol
                                    }
                                    for port in svc.spec.ports
                                ] if svc.spec.ports else []
                            }
                            all_services.append(service_info)
                        except Exception as svc_process_error:
                            logging.error(f"Error processing service {svc.metadata.name}: {svc_process_error}")
                            continue

                    all_secrets.extend([
                        {
                            "name": secret.metadata.name,
                            "namespace": secret.metadata.namespace
                        }
                        for secret in secrets.items
                    ])

                    all_configmaps.extend([
                        {
                            "name": cm.metadata.name,
                            "namespace": cm.metadata.namespace,
                            "data": cm.data if cm.data else {}
                        }
                        for cm in configmaps.items
                    ])

                except Exception as ns_error:
                    logging.error(f"Error processing namespace {ns}: {ns_error}")
                    continue

            info = {
                "pods": all_pods,
                "services": all_services,
                "secrets": all_secrets,
                "configmaps": all_configmaps
            }

            logging.debug("Summary of gathered information:")
            logging.debug(f"Total pods found: {len(all_pods)}")
            logging.debug(f"Total services found: {len(all_services)}")
            logging.debug(f"Total secrets found: {len(all_secrets)}")
            logging.debug(f"Total configmaps found: {len(all_configmaps)}")
            
            if not any([all_pods, all_services, all_secrets, all_configmaps]):
                logging.warning("No Kubernetes resources found in any namespace!")

            return info

        except Exception as e:
            logging.error(f"Error gathering K8s info: {str(e)}")
            logging.error(f"Exception type: {type(e).__name__}")
            logging.error(f"Exception details: {str(e)}")
            return {"pods": [], "services": [], "secrets": [], "configmaps": []}

    def _get_container_info(self, container) -> Dict:
        """Helper method to extract container information"""
        try:
            container_info = {
                "name": container.name,
                "ports": [],
                "env": [],
                "volume_mounts": [],
                "probes": {}
            }
            
            if container.ports:
                container_info["ports"] = [
                    {"container_port": p.container_port, 
                    "protocol": p.protocol} 
                    for p in container.ports
                ]
            
            if container.env:
                container_info["env"] = [
                    {
                        "name": env.name,
                        "value": env.value if env.value else "from_secret" if env.value_from else None,
                        "value_from": {
                            "secret_name": env.value_from.secret_key_ref.name,
                            "secret_key": env.value_from.secret_key_ref.key
                        } if env.value_from and env.value_from.secret_key_ref else None
                    }
                    for env in container.env
                ]
            
            if container.volume_mounts:
                container_info["volume_mounts"] = [
                    {
                        "name": vm.name,
                        "mount_path": vm.mount_path,
                        "sub_path": vm.sub_path
                    }
                    for vm in container.volume_mounts
                ]
            
            if container.readiness_probe:
                container_info["probes"]["readiness"] = {
                    "http_get": {
                        "path": container.readiness_probe.http_get.path,
                        "port": container.readiness_probe.http_get.port
                    } if container.readiness_probe.http_get else None,
                    "tcp_socket": {
                        "port": container.readiness_probe.tcp_socket.port
                    } if container.readiness_probe.tcp_socket else None
                }
                
            return container_info
        except Exception as e:
            logging.error(f"Error processing container {container.name}: {e}")
            return {}

    def _get_volume_info(self, volumes) -> List[Dict]:
        """Helper method to extract volume information"""
        try:
            return [
                {
                    "name": vol.name,
                    "persistent_volume_claim": vol.persistent_volume_claim.claim_name if vol.persistent_volume_claim else None,
                    "secret": vol.secret.secret_name if vol.secret else None
                }
                for vol in volumes
            ]
        except Exception as e:
            logging.error(f"Error processing volumes: {e}")
            return []

    def query_gpt(self, query: str, cluster_info: dict) -> str:
        """Query GPT with enhanced system prompt for better Harbor information retrieval"""
        try:
            system_prompt = f"""You are a Kubernetes cluster assistant specializing in Harbor deployments. Answer questions about the cluster based on this information:

            Cluster Information:
            Pods: {json.dumps(cluster_info.get('pods', []), indent=2)}
            Services: {json.dumps(cluster_info.get('services', []), indent=2)}
            Secrets: {json.dumps(cluster_info.get('secrets', []), indent=2)}
            ConfigMaps: {json.dumps(cluster_info.get('configmaps', []), indent=2)}
            
            Response Rules:
            1. Return only raw values without explanations or text
            2. For container ports, return only the number (e.g., "8080" not "port 8080")
            3. For paths, return the full path (e.g., "/data/postgresql")
            4. For environment variables, return only the value
            5. For status queries, use single words (e.g., "Running" not "Status is Running")
            6. For multiple items, separate with commas (no spaces)
            7. If information isn't found in the cluster data, respond with "Unknown"
            8. For readiness probe paths, include the full path with leading slash
            9. For PostgreSQL database names, check both environment variables and configmaps
            10. When asked about secrets, check both direct secret references and environment variables using secrets
            """
                
            response = self.openai_client.chat.completions.create(
                # model="gpt-4",
                model="gpt-3.5-turbo", 

                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error querying GPT: {e}")
            return "Error processing query"

class QueryResponse(BaseModel):
    query: str
    answer: str

def create_app():
    app = Flask(__name__)
    assistant = K8sAssistant()

    # Add Prometheus metrics endpoint
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/metrics': make_wsgi_app()
    })

    @app.route('/metrics', methods=['GET'])
    def metrics():
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy"}), 200

    @app.route('/query', methods=['POST'])
    def create_query():
        start_time = time.time()
        try:
            request_data = request.json
            query = request_data.get('query')
            logging.debug(f"Received query: {query}")
            
            QUERY_COUNTER.inc()
            
            logging.debug("Gathering cluster info...")
            cluster_info = assistant.get_k8s_info()
            
            metrics = {
                'pod_count': str(len(cluster_info.get('pods', []))),
                'service_count': str(len(cluster_info.get('services', []))),
                'configmap_count': str(len(cluster_info.get('configmaps', []))),
                'secret_count': str(len(cluster_info.get('secrets', [])))
            }
            CLUSTER_INFO.info(metrics)
            
            logging.debug("Querying GPT...")
            logging.debug(f"Cluster_info..., {cluster_info}",)
            logging.debug(f"Query Info...{query}")
            answer = assistant.query_gpt(query, cluster_info)
            logging.debug(f"Generated answer: {answer}")
            
            response = QueryResponse(query=query, answer=answer)
            return jsonify(response.model_dump())
        
        except ValidationError as e:
            ERROR_COUNTER.labels(error_type='validation').inc()
            logging.error(f"Validation error: {e}")
            return jsonify({"error": e.errors()}), 400
        except Exception as e:
            ERROR_COUNTER.labels(error_type='unexpected').inc()
            logging.error(f"Unexpected error: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            QUERY_LATENCY.observe(time.time() - start_time)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000)