#!/bin/bash

echo "Testing Kubernetes AI Query Agent..."

echo -e "\nTesting Pod Query:"
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "List all running pods"}'

echo -e "\n\nTesting Node Status:"
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "What is the status of all nodes?"}'

echo -e "\n\nTesting Deployment Count:"
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "How many deployments are there?"}'

echo -e "\n\nTesting Service Discovery:"
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d '{"query": "What services are available?"}'

echo -e "\n\nTesting Health Endpoint:"
curl http://localhost:8000/health

echo -e "\n\nTesting Metrics Endpoint:"
curl http://localhost:8000/metrics

echo -e "\nDone testing!"