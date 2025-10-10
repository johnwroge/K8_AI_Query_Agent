# Kubernetes AI Query Agent

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

An intelligent REST API that enables natural language queries about Kubernetes cluster resources using OpenAI's GPT models. Query your cluster state, monitor resources, and get insights through conversational AI.

## Features

- **Natural Language Interface**: Ask questions about your cluster in plain English
- **Real-time Cluster Analysis**: Fetch live information about pods, services, and deployments
- **Multi-namespace Support**: Query resources across different namespaces
- **Prometheus Metrics**: Built-in monitoring with Prometheus-compatible metrics


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
       ├────────────────┐
       ▼                ▼
┌──────────────┐  ┌──────────────┐
│  K8s Client  │  │ AI Service   │
│ (k8s_client) │  │ (ai_service) │
└──────┬───────┘  └──────┬───────┘
       │                  │
       ▼                  ▼
┌──────────────┐  ┌──────────────┐
│ Kubernetes   │  │  OpenAI API  │
│   Cluster    │  │              │
└──────────────┘  └──────────────┘
```

## Prerequisites

- Python 3.10 or higher
- Kubernetes cluster (local or remote)
  - Minikube for local development
  - kubectl configured with cluster access
- OpenAI API key
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
OPENAI_MODEL=gpt-3.5-turbo
LOG_LEVEL=INFO
APP_PORT=8000
```

## ⚙️ Configuration

The application can be configured through environment variables or the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | GPT model to use | `gpt-3.5-turbo` |
| `OPENAI_TEMPERATURE` | Model temperature | `0.0` |
| `APP_HOST` | Server host | `0.0.0.0` |
| `APP_PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `K8S_NAMESPACE_FILTER` | Filter namespaces | `None` |

## 💻 Usage

### Local Development

1. **Start the Application**

```bash
python main.py
```

2. **Make a Query**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many pods are running in the default namespace?"}'
```

3. **Check Health**

```bash
curl http://localhost:8000/health
```

### Docker Deployment

1. **Build Image**

```bash
docker build -t k8s-ai-agent:latest .
```

2. **Run Container**

```bash
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  --name k8s-agent \
  k8s-ai-agent:latest
```

## 📖 API Reference

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
  "answer": "nginx,mongodb,prometheus,k8s-agent",
  "processing_time_ms": 1234.56
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request
- `500`: Server error

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "kubernetes": "connected",
    "ai_service": "connected",
    "model": "gpt-3.5-turbo"
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

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test file
python -m pytest test_k8s_agent.py -v
```

### Run Integration Tests

```bash
# Requires running cluster and OpenAI API key
python -m pytest -m integration
```

### Test Examples

```python
# Test health endpoint
python -m pytest test_k8s_agent.py::TestFlaskApp::test_health_check_success

# Test query processing
python -m pytest test_k8s_agent.py::TestFlaskApp::test_query_success
```

## 🚢 Kubernetes Deployment

### 1. Create OpenAI Secret

```bash
# Encode your API key
echo -n "your-openai-api-key" | base64

# Create secret manifest
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: openai-api-key
type: Opaque
data:
  api-key: <your-base64-encoded-key>
EOF
```

### 2. Deploy Application

```bash
# Build image with Minikube's Docker daemon
eval $(minikube docker-env)
docker build -t k8s-ai-agent:latest .

# Apply deployment
kubectl apply -f deployment.yaml

# Verify deployment
kubectl get pods -l app=k8s-agent
```

### 3. Expose Service

```bash
# Port forward for testing
kubectl port-forward service/k8s-agent-service 8000:80

# Or create an ingress for production
kubectl apply -f ingress.yaml
```

## 📊 Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at `/metrics`:

- `k8s_agent_queries_total`: Total queries processed
- `k8s_agent_query_duration_seconds`: Query processing latency
- `k8s_agent_errors_total`: Total errors by type
- `k8s_agent_cluster_info`: Current cluster information

### View Metrics

```bash
curl http://localhost:8000/metrics
```

### Grafana Dashboard

Import the provided Grafana dashboard configuration:

```bash
kubectl apply -f grafana-dashboard.json
```

## 🔍 Example Queries

### Cluster Information

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

## 🐛 Troubleshooting

### Common Issues

**Issue: "Failed to connect to Kubernetes cluster"**
- Verify kubectl is configured: `kubectl cluster-info`
- Check kubeconfig: `echo $KUBECONFIG`
- Ensure cluster is running: `minikube status`

**Issue: "OpenAI API error"**
- Verify API key is correct in `.env`
- Check API key has sufficient credits
- Verify network connectivity to OpenAI

**Issue: "Pod is not running"**
- Check pod logs: `kubectl logs -f <pod-name>`
- Describe pod: `kubectl describe pod <pod-name>`
- Verify secret is created: `kubectl get secret openai-api-key`

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python main.py
```

View logs:

```bash
tail -f agent.log
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.




