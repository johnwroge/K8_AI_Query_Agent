# Kubernetes AI Query Agent

An AI-powered agent that answers queries about your Kubernetes cluster.

## Prerequisites
- Python 3.10
- Minikube
- kubectl
- OpenAI API key

## Installation

1. Clone the repository

`git clone https://github.com/johnwroge/K8_AI_Query_Agent.git`

`cd k8_AI_Agent`

2. Create virtual environment

`python3.10 -m venv venv`

Activate on Mac:

`source venv/bin/activate`

Activate on Windows

`.\venv\Scripts\activate`

3. Install Dependencies

`pip install -r requirements.txt`

4. Create env variable in env file. 

`OPENAI_API_KEY=your-api-key-here`


## Kubernetes Setup


1. Start Minikube

`minikube start`

2. Verify cluster is running

`minikube status`

`kubectl get nodes`

3. Deploy sample applications

### Deploy nginx

`kubectl create deployment nginx --image=nginx`

`kubectl expose deployment nginx --port=80`

### Deploy MongoDB

`kubectl create deployment mongodb --image=mongo`

`kubectl expose deployment mongodb --port=27017`

### Deploy Prometheus

`kubectl apply -f prometheus.yaml`

### Verify deployments

`kubectl get pods,deployments,services`


## Running the Agent


1. Start the flask server

`python main.py`

2. Monitor logs

`tail -f agent.log`

# Running Tests

`python -m unittest test_main.py`


### Example Curl Requests

Check Nodes:

```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "How many nodes are in the cluster?"}'
```

Response: {"answer":"1","query":"How many nodes are in the cluster?"}

Check Pods:

```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "How many pods are in the default namespace?"}'
```

Response: {"answer":"3","query":"How many pods are in the default namespace?"}

Check deployments:

```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "What deployments are running?"}'
```

Response: {"answer":"mongodb,nginx,prometheus","query":"What deployments are running?"}

Check services:
```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "What services are running in the default namespace?"}'
```
Response: {"answer":"kubernetes,mongodb,prometheus","query":"What services are running in the default namespace?"}


# Cluster Management / Teardown 

## Stop Minikube

`minikube stop`

## Delete cluster

`minikube delete`


