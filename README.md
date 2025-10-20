# Kubernetes AI Query Agent

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An intelligent REST API that enables natural language queries about Kubernetes cluster resources and provides AI-powered debugging for pod crashes and failures. Query your cluster state, monitor resources, get insights through conversational AI, and debug issues in seconds instead of hours.

## Features

**Natural Language Interface**: Ask questions about your cluster in plain English

**AI-Powered Pod Debugging**: Instantly diagnose crashed pods with root cause analysis and actionable fixes

**Real-time Cluster Analysis**: Fetch live information about pods, services, and deployments

**Pattern Detection**: Automatically identifies common issues (CrashLoopBackOff, OOMKilled, ImagePullBackOff)

**Actionable Fixes**: Get exact kubectl commands to investigate and resolve issues

**Multi-namespace Support**: Query and debug resources across different namespaces

**Prometheus Metrics**: Built-in monitoring with Prometheus-compatible metrics

## What's New: Pod Crash Analyzer

**Problem**: Developers waste 15-30 minutes debugging common Kubernetes issues.

**Solution**: Get instant root cause analysis with specific fix commands in under 3 seconds.

```bash
# Before: Manual debugging (15-30 minutes)
kubectl get pods
kubectl describe pod my-app
kubectl logs my-app --previous
# ... trial and error ...

# After: AI-powered debugging (30 seconds)
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "my-app"}' | jq
```

**Detects:**
- CrashLoopBackOff
- OOMKilled (Out of Memory)
- ImagePullBackOff
- Configuration errors
- Network connectivity issues
- Permission errors

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────────────┐
│   Flask API         │
│   (main.py)         │
└──────┬──────────────┘
       │
       ├────────────────┬──────────────────┐
       ▼                ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  K8s Client  │  │ K8s Analyzer │  │ AI Service   │
│              │  │ (Deep Debug) │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                  │                  │
       │                  ├──────────────────┤
       │                  ▼                  ▼
       │         ┌──────────────────┐  ┌──────────────┐
       │         │ Debug Assistant  │  │  OpenAI API  │
       │         │ • Pattern detect │  │  (GPT-4o)    │
       │         │ • AI analysis    │  │              │
       │         └──────────────────┘  └──────────────┘
       ▼
┌──────────────┐
│ Kubernetes   │
│   Cluster    │
└──────────────┘
```

## Prerequisites

- Python 3.10 or higher
- Kubernetes cluster (local or remote)
  - Minikube for local development
  - kubectl configured with cluster access
- OpenAI API key (required for debugging features)
- Docker (for containerized deployment)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/johnwroge/K8_AI_Query_Agent.git
cd K8_AI_Query_Agent
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
.\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
APP_PORT=8000
```

## Configuration

The application can be configured through environment variables or the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | GPT model to use | `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | Model temperature | `0.0` |
| `APP_HOST` | Server host | `0.0.0.0` |
| `APP_PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `K8S_NAMESPACE_FILTER` | Filter namespaces | `None` |

## Usage

### Local Development

**1. Start the Application**

```bash
# From project root
python run.py

# Or using module syntax
python -m src.main
```

**2. Debug a Crashed Pod**

```bash
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "my-crashing-pod", "namespace": "default"}'
```

**3. Make a Natural Language Query**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many pods are running in the default namespace?"}'
```

**4. Check Health**

```bash
curl http://localhost:8000/health
```

### Docker Deployment

**1. Build Image**

```bash
docker build -t k8s-ai-agent:latest .
```

**2. Run Container**

```bash
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  --name k8s-agent \
  k8s-ai-agent:latest
```

## API Reference

### POST /debug/pod-crash

Debug a crashed or failing pod with AI-powered analysis.

**Request Body:**
```json
{
  "pod_name": "my-app-deployment-xyz",
  "namespace": "default"
}
```

**Response:**
```json
{
  "success": true,
  "pod_name": "my-app-deployment-xyz",
  "namespace": "default",
  "issue_type": "CrashLoopBackOff",
  "root_cause": "Container exits with code 1 - Database connection failed",
  "explanation": "The container is repeatedly crashing because it cannot connect to the database at postgres:5432...",
  "detected_patterns": ["CrashLoopBackOff", "Database connection error in logs"],
  "likely_causes": [
    "Database connection string incorrect in environment variables",
    "Service 'postgres' not accessible from this namespace",
    "Database credentials are missing or invalid"
  ],
  "suggested_fixes": [
    {
      "action": "Verify DATABASE_URL environment variable",
      "command": "kubectl get pod my-app-xyz -o jsonpath='{.spec.containers[0].env}'",
      "why": "Check if the database connection string is correctly configured"
    }
  ],
  "severity": "high",
  "quick_fix_available": false,
  "confidence": "high",
  "processing_time_ms": 2347.82
}
```

**Status Codes:**
- `200`: Success - pod analyzed
- `404`: Pod not found
- `400`: Invalid request
- `500`: Server error

### POST /query

Process a natural language query about the cluster.

**Request Body:**
```json
{
  "query": "What pods are running?",
  "namespace": "default"
}
```

**Response:**
```json
{
  "query": "What pods are running?",
  "answer": "nginx, mongodb, prometheus, k8s-agent",
  "processing_time_ms": 1234.56
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "kubernetes": "connected",
    "ai_service": "connected",
    "model": "gpt-4o-mini",
    "debug_assistant": "ready"
  }
}
```

### GET /namespaces

List all namespaces in the cluster.

**Response:**
```json
{
  "namespaces": ["default", "kube-system", "kube-public"]
}
```

### GET /metrics

Prometheus metrics endpoint for monitoring.

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_k8s_agent.py -v
pytest tests/test_debug_assistant.py -v
```

### Test Pod Debugging with Real Scenarios

```bash
# Deploy test pods with intentional issues
kubectl apply -f deployment/test-broken-pods.yaml

# Wait for pods to enter crash states
sleep 15

# Debug each scenario
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "crash-loop-test"}' | jq

curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "oom-test"}' | jq

# Cleanup
kubectl delete -f deployment/test-broken-pods.yaml
```

### Test Examples

```bash
# Test health endpoint
pytest tests/test_k8s_agent.py::TestFlaskApp::test_health_check_success

# Test query processing
pytest tests/test_k8s_agent.py::TestFlaskApp::test_query_success

# Test debug pattern detection
pytest tests/test_debug_assistant.py::TestDebugAssistant::test_detect_crashloopbackoff
```

## Deployment

### 1. Create OpenAI Secret

```bash

# Create secret from example
cp deployment/openai-secret.example.yaml deployment/openai-secret.yaml

# Edit the file with your actual API key (no encoding needed)
vim deployment/openai-secret.yaml

# Apply the secret (Kubernetes automatically converts stringData to base64-encoded data when you apply it)
kubectl apply -f deployment/openai-secret.yaml

# Verify it was created
kubectl get secret openai-secret
```

### 2. Deploy Application

```bash
# Build image with Minikube's Docker daemon
eval $(minikube docker-env)
docker build -t k8s-ai-agent:latest .

# Apply deployment
kubectl apply -f deployment/deployment.yaml

# Verify deployment
kubectl get pods -l app=k8s-agent
```

### 3. Expose Service

```bash
# Port forward for testing
kubectl port-forward service/k8s-agent-service 8000:80

# Or create an ingress for production
kubectl apply -f deployment/ingress.yaml
```

## Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at `/metrics`:

**Existing Metrics:**
- `k8s_agent_queries_total`: Total queries processed
- `k8s_agent_query_duration_seconds`: Query processing latency
- `k8s_agent_errors_total`: Total errors by type
- `k8s_agent_cluster_info`: Current cluster information

**Debug Metrics:**
- `k8s_agent_debug_requests_total{issue_type}`: Debug requests by issue type
- `k8s_agent_debug_duration_seconds`: Debug processing time

### View Metrics

```bash
curl http://localhost:8000/metrics
```

### Grafana Dashboard

Import the provided Grafana dashboard configuration:

```bash
kubectl apply -f deployment/prometheus.yaml
```

## Example Queries

### Pod Debugging Examples

```bash
# Debug a CrashLoopBackOff
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "failing-app"}'

# Debug in specific namespace
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "backend-service", "namespace": "production"}'
```

### Cluster Information Queries

```bash
# Count pods
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many pods are running?"}'

# List deployments
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What deployments exist?"}'

# Check pod status
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of nginx pod?"}'
```

### Multi-Namespace Queries

```bash
# Query specific namespace
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List all services", "namespace": "kube-system"}'
```

## Troubleshooting

### Common Issues

**Issue: "Failed to connect to Kubernetes cluster"**
- Verify kubectl is configured: `kubectl cluster-info`
- Check kubeconfig: `echo $KUBECONFIG`
- Ensure cluster is running: `minikube status`

**Issue: "OpenAI API key is required"**
- Verify API key is set: `echo $OPENAI_API_KEY`
- Check .env file exists and contains key
- Ensure key has sufficient credits at OpenAI

**Issue: "OpenAI API error"**
- Verify API key is correct in `.env`
- Check API key has sufficient credits
- Verify network connectivity to OpenAI
- Check OpenAI service status

**Issue: "Pod is not running"**
- Check pod logs: `kubectl logs -f <pod-name>`
- Describe pod: `kubectl describe pod <pod-name>`
- Verify secret is created: `kubectl get secret openai-api-key`

**Issue: "Debug endpoint returns fallback response"**
- This is normal - pattern detection still works without AI
- Check logs for specific OpenAI errors: `tail -f agent.log`
- Verify OPENAI_API_KEY is valid
- Check OpenAI API quota/limits

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python run.py
```

View logs:

```bash
tail -f agent.log
```

## Documentation

- **[Setup & Test Guide](docs/SETUP_AND_TEST_GUIDE.md)** - Comprehensive setup and testing instructions
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Quick command reference card
- **[Model Configuration](docs/MODEL_CONFIGURATION_GUIDE.md)** - AI model options and cost comparison
- **[Roadmap](roadmap.md)** - Feature roadmap and future plans

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [OpenAI GPT-4](https://openai.com/)
- [Flask](https://flask.palletsprojects.com/)
- [Prometheus Client](https://github.com/prometheus/client_python)