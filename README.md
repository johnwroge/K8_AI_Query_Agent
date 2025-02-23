# Kubernetes AI Query Agent

**Note:** This AI Agent is currently under development

An AI-powered agent that answers queries about your Kubernetes cluster using Open AI. This tool enables natural language queries about your Kubernetes resources and provides concise, accurate responses about the state of your cluster.

Uses natural language processing to:
- Fetch real-time information about pods, services, secrets, and configmaps
- Interpret cluster state and configurations
- Monitor cluster health through Prometheus metrics

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Local Development Setup](#local-development-setup)
- [Kubernetes Deployment Setup](#kubernetes-deployment-setup)
- [Usage](#usage)
- [Example Queries](#example-queries)
- [Cluster Management](#cluster-management)
- [Troubleshooting](#troubleshooting)

## Prerequisites
- Python 3.10
- Minikube
- kubectl
- Docker
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/johnwroge/K8_AI_Query_Agent.git
cd k8_AI_Agent
```

2. Create and activate virtual environment:
```bash
# Create environment
python3.10 -m venv venv

# Activate on Mac/Linux:
source venv/bin/activate

# Activate on Windows:
.\venv\Scripts\activate
```

3. Install Dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with your OpenAI API key:
```bash
OPENAI_API_KEY=your-api-key-here
```

## Local Development Setup

1. Start the flask server:
```bash
python main.py
```

2. Monitor logs:
```bash
tail -f agent.log
```

3. Test the application:
```bash
python -m unittest test_main.py
```

## Kubernetes Deployment Setup

1. Start Minikube:
```bash
minikube start
minikube status
kubectl get nodes
```

2. Create OpenAI Secret:
```bash
# Generate base64 encoded API key
echo -n "your-actual-openai-key" | base64

# Create openai-secret.yaml (DO NOT commit this file)
apiVersion: v1
kind: Secret
metadata:
  name: openai-api-key
type: Opaque
data:
  api-key: <your-base64-encoded-api-key>

# Apply the secret
kubectl apply -f openai-secret.yaml
```

3. Build and Deploy Application:
```bash
# Configure Docker to use Minikube's daemon
eval $(minikube docker-env)

# Build the image
docker build -t k8s-agent:latest .

# Apply deployment configuration
kubectl apply -f deployment.yaml
```

4. Deploy Sample Applications:
```bash
# Deploy NGINX
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80

# Deploy MongoDB
kubectl create deployment mongodb --image=mongo
kubectl expose deployment mongodb --port=27017

# Deploy Prometheus
kubectl apply -f prometheus.yaml
```

5. Verify Deployments:
```bash
kubectl get pods,deployments,services
```

## Usage

1. Set up port forwarding:
```bash
kubectl port-forward service/k8s-agent-service 8000:80
```

2. The API will be available at `http://localhost:8000`

## Example Queries

Check Nodes:
```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "How many nodes are in the cluster?"}'
```
Response: `{"answer":"1","query":"How many nodes are in the cluster?"}`

Check Pods:
```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "How many pods are in the default namespace?"}'
```
Response: `{"answer":"4","query":"How many pods are in the default namespace?"}`

Check Deployments:
```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "What deployments are running?"}'
```
Response: `{"answer":"k8s-agent,mongodb,nginx,prometheus","query":"What deployments are running?"}`

## Test Script

The test_api.sh file can be updated to make requests to the API for desired metrics. 

```bash
chmod +x test_api.sh

./test_api.sh
```

## API Model Configuration

This project uses OpenAI's gpt-3.5-turbo by default for cost-effective development and testing.
You can switch to GPT-4 for better language capabilities:

```python
response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0
            )
```

## Cluster Management

Stop Minikube:
```bash
minikube stop
```

Delete Cluster:
```bash
minikube delete
```

## Troubleshooting

Common issues and solutions:

1. OpenAI API Issues:
   - Verify API key is correct in .env file
   - Check API key is properly encoded in secret

2. Kubernetes Issues:
   - Check Minikube status: `minikube status`
   - Verify pods are running: `kubectl get pods`
   - Check pod logs: `kubectl logs -f <pod-name>`

3. Docker Issues:
   - Ensure using Minikube's Docker daemon: `eval $(minikube docker-env)`
   - Rebuild image if needed: `docker build -t k8s-agent:latest .`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
