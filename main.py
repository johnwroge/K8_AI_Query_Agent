import logging
import os
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
from kubernetes import client as k8s_client, config
from openai import OpenAI
import openai
from typing import List
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
import time

load_dotenv()

openai_client = OpenAI()

api_key = os.getenv('OPENAI_API_KEY')


QUERY_COUNTER = Counter('k8s_agent_queries_total', 'Total number of queries processed')
QUERY_LATENCY = Histogram('k8s_agent_query_duration_seconds', 'Time spent processing queries')
ERROR_COUNTER = Counter('k8s_agent_errors_total', 'Total number of errors', ['error_type'])
CLUSTER_INFO = Info('k8s_agent_cluster', 'Kubernetes cluster information')

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s %(levelname)s - %(message)s',
                   filename='agent.log', filemode='a')
logging.getLogger().addHandler(logging.StreamHandler())  


logging.info("Testing OpenAI connection...")

try:
    test_response = openai_client.chat.completions.create(
        model="gpt-4",  
        messages=[{"role": "user", "content": "Say hello"}],
        temperature=0
    )
    logging.info("OpenAI connection successful")
except Exception as e:
    logging.error(f"OpenAI error: {e}")

app = Flask(__name__)

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

try:
    if os.getenv('KUBERNETES_SERVICE_HOST'):
        config.load_incluster_config()
    else:
        config.load_kube_config()
        
    v1 = k8s_client.CoreV1Api()
    apps_v1 = k8s_client.AppsV1Api()
    logging.info("Successfully connected to Kubernetes cluster")
except Exception as e:
    logging.error(f"Failed to connect to Kubernetes cluster: {e}")


class QueryResponse(BaseModel):
    query: str
    answer: str

def get_k8s_info() -> dict:
    """Gather information about the Kubernetes cluster"""
    info = {}
    try:
        logging.debug("Attempting to list pods...")
        pods = v1.list_namespaced_pod("default")
        info["pods"] = [{"name": p.metadata.name, "status": p.status.phase} for p in pods.items]
        logging.debug(f"Found pods: {info['pods']}")
        
        logging.debug("Attempting to list nodes...")
        nodes = v1.list_node()
        info["nodes"] = [{"name": n.metadata.name} for n in nodes.items]
        logging.debug(f"Found nodes: {info['nodes']}")
        
        logging.debug("Attempting to list deployments...")
        deployments = apps_v1.list_namespaced_deployment("default")
        info["deployments"] = [{"name": d.metadata.name} for d in deployments.items]
        logging.debug(f"Found deployments: {info['deployments']}")

        logging.debug("Attempting to list services...")
        services = v1.list_namespaced_service("default")
        info["services"] = [{"name": s.metadata.name} for s in services.items]
        logging.debug(f"Found services: {info['services']}")
        
    except Exception as e:
        logging.error(f"Error gathering K8s info: {e}")
    return info

def query_gpt(query: str, cluster_info: dict) -> str:
    try:
        system_prompt = f"""You are a Kubernetes cluster assistant. Answer questions about the cluster based on this information:
                Cluster Status:
                Pods: {cluster_info.get('pods', [])}
                Nodes: {cluster_info.get('nodes', [])}
                Deployments: {cluster_info.get('deployments', [])}
                Services: {cluster_info.get('services', [])}
                
                Response Rules:
                1. Return only raw values without explanations or text
                2. Strip all identifiers/hashes (e.g., use "mongodb" not "mongodb-56c598c8fc")
                3. For status queries, use single words (e.g., "Running" not "Container is Running")
                4. For counts, return only the number (e.g., "2" not "2 pods")
                5. For multiple items, separate with commas (e.g., "mongodb,nginx,redis")
                6. If uncertain, respond with "Unknown"
                """
        response = openai_client.chat.completions.create(
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

def update_cluster_metrics(cluster_info: dict):
    """Update Prometheus metrics with cluster information"""
    metrics = {
        'pod_count': str(len(cluster_info.get('pods', []))),
        'node_count': str(len(cluster_info.get('nodes', []))),
        'deployment_count': str(len(cluster_info.get('deployments', []))),
        'service_count': str(len(cluster_info.get('services', [])))
    }
    CLUSTER_INFO.info(metrics)


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
        cluster_info = get_k8s_info()
        logging.debug(f"Cluster info: {cluster_info}")
        update_cluster_metrics(cluster_info)
        
        logging.debug("Querying GPT...")
        answer = query_gpt(query, cluster_info)
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)