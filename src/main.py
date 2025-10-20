"""
Main application module for Kubernetes AI Debug Assistant.
Provides a Flask REST API for debugging Kubernetes pods using AI.
"""
import logging
import time
from typing import Dict, Any
from flask import Flask, request, jsonify
from pydantic import BaseModel, ValidationError, field_validator
from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from dotenv import load_dotenv

from k8s_client import K8sClient
from ai_service import AIQueryService
from debug_assistant import DebugAssistant

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
QUERY_COUNTER = Counter(
    'k8s_agent_queries_total', 
    'Total number of queries processed'
)
DEBUG_COUNTER = Counter(
    'k8s_agent_debug_requests_total',
    'Total number of debug requests processed',
    ['issue_type']
)
QUERY_LATENCY = Histogram(
    'k8s_agent_query_duration_seconds', 
    'Time spent processing queries'
)
DEBUG_LATENCY = Histogram(
    'k8s_agent_debug_duration_seconds',
    'Time spent processing debug requests'
)
ERROR_COUNTER = Counter(
    'k8s_agent_errors_total', 
    'Total number of errors', 
    ['error_type']
)
CLUSTER_INFO_METRIC = Info(
    'k8s_agent_cluster', 
    'Kubernetes cluster information'
)


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str
    namespace: str = "default"
    
    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class DebugPodRequest(BaseModel):
    """Request model for pod crash debugging endpoint."""
    pod_name: str
    namespace: str = "default"
    
    @field_validator('pod_name')
    @classmethod
    def pod_name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Pod name cannot be empty')
        return v.strip()


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query: str
    answer: str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    components: Dict[str, str]


def create_app(
    k8s_client: K8sClient = None,
    ai_service: AIQueryService = None,
    debug_assistant: DebugAssistant = None
) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        k8s_client: Optional K8sClient instance (for testing)
        ai_service: Optional AIQueryService instance (for testing)
        debug_assistant: Optional DebugAssistant instance (for testing)
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Initialize services
    try:
        if k8s_client is None:
            k8s_client = K8sClient()
        if ai_service is None:
            ai_service = AIQueryService()
        if debug_assistant is None:
            debug_assistant = DebugAssistant()
        
        logger.info("Application services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    # Add Prometheus metrics endpoint
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app,
        {'/metrics': make_wsgi_app()}
    )
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        try:
            # Basic health checks
            namespaces = k8s_client.get_namespaces()
            model_info = ai_service.get_model_info()
            
            health = HealthResponse(
                status="healthy",
                components={
                    "kubernetes": "connected",
                    "ai_service": "connected",
                    "model": model_info["model"],
                    "debug_assistant": "ready"
                }
            )
            return jsonify(health.model_dump()), 200
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 503
    
    @app.route('/debug/pod-crash', methods=['POST'])
    def debug_pod_crash():
        """
        Debug a crashing or failing pod and provide actionable fixes.
        
        Request body:
            {
                "pod_name": "my-app-xyz",
                "namespace": "default"  // optional, defaults to "default"
            }
        
        Returns:
            JSON response with root cause analysis and suggested fixes
        """
        start_time = time.time()
        
        try:
            # Validate request
            request_data = request.get_json(silent=True)
            if not request_data:
                return jsonify({"error": "Request body is required"}), 400
            
            debug_request = DebugPodRequest(**request_data)
            logger.info(f"Processing debug request for pod: {debug_request.pod_name}")
            
            # Perform debugging
            result = debug_assistant.debug_pod(
                pod_name=debug_request.pod_name,
                namespace=debug_request.namespace
            )
            
            # Update metrics
            if result.get("success"):
                issue_type = result.get("issue_type", "unknown")
                DEBUG_COUNTER.labels(issue_type=issue_type).inc()
            else:
                ERROR_COUNTER.labels(error_type='pod_not_found').inc()
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            result["processing_time_ms"] = round(processing_time, 2)
            
            status_code = 200 if result.get("success") else 404
            return jsonify(result), status_code
            
        except ValidationError as e:
            ERROR_COUNTER.labels(error_type='validation').inc()
            logger.warning(f"Validation error: {e}")
            error_details = [
                {
                    "field": ".".join(str(x) for x in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"]
                }
                for err in e.errors()
            ]
            return jsonify({"error": "Invalid request", "details": error_details}), 400
            
        except Exception as e:
            ERROR_COUNTER.labels(error_type='unexpected').inc()
            logger.error(f"Unexpected error processing debug request: {e}", exc_info=True)
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
            
        finally:
            DEBUG_LATENCY.observe(time.time() - start_time)
    
    @app.route('/query', methods=['POST'])
    def query():
        """
        Process a natural language query about the Kubernetes cluster.
        
        Request body:
            {
                "query": "How many pods are running?",
                "namespace": "default"  // optional
            }
        
        Returns:
            JSON response with query answer
        """
        start_time = time.time()
        
        try:
            # Validate request
            request_data = request.get_json(silent=True)
            if not request_data:
                return jsonify({"error": "Request body is required"}), 400
            
            query_request = QueryRequest(**request_data)
            logger.info(f"Processing query: {query_request.query}")
            
            QUERY_COUNTER.inc()
            
            # Gather cluster information
            namespaces = [query_request.namespace]
            cluster_data = k8s_client.get_cluster_summary(namespaces)
            
            # Update Prometheus metrics
            CLUSTER_INFO_METRIC.info({
                'pod_count': str(len(cluster_data.get('pods', []))),
                'service_count': str(len(cluster_data.get('services', []))),
                'deployment_count': str(len(cluster_data.get('deployments', [])))
            })
            
            # Process query with AI
            answer = ai_service.query(query_request.query, cluster_data)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            response = QueryResponse(
                query=query_request.query,
                answer=answer,
                processing_time_ms=round(processing_time, 2)
            )
            
            return jsonify(response.model_dump()), 200
            
        except ValidationError as e:
            ERROR_COUNTER.labels(error_type='validation').inc()
            logger.warning(f"Validation error: {e}")
            error_details = [
                {
                    "field": ".".join(str(x) for x in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"]
                }
                for err in e.errors()
            ]
            return jsonify({"error": "Invalid request", "details": error_details}), 400
            
        except Exception as e:
            ERROR_COUNTER.labels(error_type='unexpected').inc()
            logger.error(f"Unexpected error processing query: {e}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500
            
        finally:
            QUERY_LATENCY.observe(time.time() - start_time)
    
    @app.route('/namespaces', methods=['GET'])
    def list_namespaces():
        """List all namespaces in the cluster."""
        try:
            namespaces = k8s_client.get_namespaces()
            return jsonify({"namespaces": namespaces}), 200
        except Exception as e:
            logger.error(f"Error listing namespaces: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app


if __name__ == "__main__":
    app = create_app()
    logger.info("Starting Kubernetes AI Debug Assistant on port 8000")
    app.run(host="0.0.0.0", port=8000, debug=False)