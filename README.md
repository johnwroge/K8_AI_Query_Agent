
# Kubernetes AI Query Agent

An AI-powered agent that answers queries about your Kubernetes cluster using GPT-4. This tool enables natural language queries about your Kubernetes resources and provides concise, accurate responses about the state of your cluster.

## API Model Choice

TThis project is configured to use OpenAI's GPT-4 model as specified in the requirements. However, for cost-effective development and testing, you can switch to GPT-3.5-turbo by updating the model parameter in the `query_gpt` function:


```python
 response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0
        )
```


## Prerequisites
- Python 3.10
- Minikube
- kubectl
- OpenAI API key

## Installation

1. Clone the repository

```bash
git clone https://github.com/johnwroge/K8_AI_Query_Agent.git
```

```bash
cd k8_AI_Agent
```

2. Create virtual environment

```bash
python3.10 -m venv venv
```

Activate on Mac:

```bash
source venv/bin/activate
```

Activate on Windows

```bash
.\venv\Scripts\activate
```

3. Install Dependencies

```bash
pip install -r requirements.txt
```
4. Create env variable in env file. 

```bash
OPENAI_API_KEY=your-api-key-here
```

## Kubernetes Setup


1. Start Minikube

```bash
minikube start
```

2. Verify cluster is running

```bash
minikube status
```
```bash
kubectl get nodes
```

3. Apply deployment configuration

Create RBAC and service account
```bash
kubectl apply -f deployment.yaml
```

4. Deploy sample applications

### Deploy nginx

```bash
kubectl create deployment nginx --image=nginx
```
```bash
kubectl expose deployment nginx --port=80
```

### Deploy MongoDB

```bash
kubectl create deployment mongodb --image=mongo
```
```bash
kubectl expose deployment mongodb --port=27017
```

### Deploy Prometheus

```bash
kubectl apply -f prometheus.yaml
```

### Verify deployments

```bash
kubectl get pods,deployments,services
```

## Running the Agent


1. Start the flask server

```bash
python main.py
```

2. Monitor logs

```bash
tail -f agent.log
```

# Running Tests

```bash
python -m unittest test_main.py
```


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

```bash
minikube stop
```

## Delete cluster

```bash
minikube delete
```

## Troubleshooting

If you encounter any issues:

1. Check your OpenAI API key is properly set in .env
2. Verify Minikube is running: `minikube status`
3. Check pods are running: `kubectl get pods`
4. Check logs: `tail -f agent.log`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


