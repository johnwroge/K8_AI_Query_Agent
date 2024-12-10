import logging
import os
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError
from kubernetes import client as k8s_client, config
from openai import OpenAI
import openai
print(openai.__version__)

from typing import List
from dotenv import load_dotenv

load_dotenv()


openai_client = OpenAI()

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s %(levelname)s - %(message)s',
                   filename='agent.log', filemode='a')

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

try:
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
        pods = v1.list_namespaced_pod("default")
        info["pods"] = [{"name": p.metadata.name, "status": p.status.phase} for p in pods.items]
        logging.info(f"Found pods: {info['pods']}")
        
        nodes = v1.list_node()
        info["nodes"] = [{"name": n.metadata.name} for n in nodes.items]
        logging.info(f"Found nodes: {info['nodes']}")
        
        deployments = apps_v1.list_namespaced_deployment("default")
        info["deployments"] = [{"name": d.metadata.name} for d in deployments.items]
        logging.info(f"Found deployments: {info['deployments']}")

        services = v1.list_namespaced_service("default")
        info["services"] = [{"name": s.metadata.name} for s in services.items]
        logging.info(f"Found services: {info['services']}")
        
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

@app.route('/query', methods=['POST'])
def create_query():
    try:
        request_data = request.json
        query = request_data.get('query')
        logging.info(f"Received query: {query}")
    
        cluster_info = get_k8s_info()
        
        answer = query_gpt(query, cluster_info)
        logging.info(f"Generated answer: {answer}")
        
        response = QueryResponse(query=query, answer=answer)
        return jsonify(response.model_dump())
    
    except ValidationError as e:
        logging.error(f"Validation error: {e}")
        return jsonify({"error": e.errors()}), 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)