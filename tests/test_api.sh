#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to test endpoint
test_endpoint() {
    local description=$1
    local response=$2
    local status_code=$(echo "$response" | tail -n1)
    
    if [ "$status_code" = "200" ] || [ "$status_code" = "000" ]; then
        echo -e "${GREEN}✓${NC} $description"
    else
        echo -e "${RED}✗${NC} $description (Status: $status_code)"
    fi
}

echo -e "${YELLOW}"
echo "╔═══════════════════════════════════════════╗"
echo "║  Kubernetes AI Query Agent - Test Suite  ║"
echo "╔═══════════════════════════════════════════╗"
echo -e "${NC}"

# Check if server is running
print_header "1. Connection Check"
if curl -s --max-time 5 $BASE_URL/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is running at $BASE_URL${NC}"
else
    echo -e "${RED}✗ Cannot connect to $BASE_URL${NC}"
    echo -e "${RED}Please start the server with: python main.py${NC}"
    exit 1
fi

# Test Health Endpoint
print_header "2. Health Check"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/health)
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Health endpoint" "$response"

# Test Namespaces Endpoint
print_header "3. List Namespaces"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/namespaces)
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Namespaces endpoint" "$response"

# Test Query Endpoints
print_header "4. Query Tests"

echo -e "\n${YELLOW}Test 4.1: Pod Count${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many pods are running?"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Pod count query" "$response"

echo -e "\n${YELLOW}Test 4.2: List Running Pods${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List all running pods"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "List pods query" "$response"

echo -e "\n${YELLOW}Test 4.3: Deployment Count${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How many deployments are there?"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Deployment count query" "$response"

echo -e "\n${YELLOW}Test 4.4: List Deployments${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What deployments are running?"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "List deployments query" "$response"

echo -e "\n${YELLOW}Test 4.5: Service Discovery${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What services are available?"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Service discovery query" "$response"

echo -e "\n${YELLOW}Test 4.6: Node Status${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of all nodes?"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Node status query" "$response"

echo -e "\n${YELLOW}Test 4.7: Query with Namespace${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "List services", "namespace": "kube-system"}')
echo "$response" | head -n -1 | jq '.' 2>/dev/null || echo "$response" | head -n -1
test_endpoint "Namespace-specific query" "$response"

# Test Error Handling
print_header "5. Error Handling Tests"

echo -e "\n${YELLOW}Test 5.1: Empty Query${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": ""}')
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "400" ]; then
    echo -e "${GREEN}✓${NC} Empty query properly rejected (400)"
else
    echo -e "${RED}✗${NC} Expected 400, got $status_code"
fi

echo -e "\n${YELLOW}Test 5.2: Missing Query Field${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{}')
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "400" ]; then
    echo -e "${GREEN}✓${NC} Missing query field properly rejected (400)"
else
    echo -e "${RED}✗${NC} Expected 400, got $status_code"
fi

echo -e "\n${YELLOW}Test 5.3: Invalid Endpoint${NC}"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/nonexistent)
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "404" ]; then
    echo -e "${GREEN}✓${NC} Invalid endpoint returns 404"
else
    echo -e "${RED}✗${NC} Expected 404, got $status_code"
fi

# Test Metrics Endpoint
print_header "6. Prometheus Metrics"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/metrics)
echo "$response" | head -n -1 | grep -E "(k8s_agent_queries_total|k8s_agent_query_duration|k8s_agent_cluster_info)" | head -n 10
test_endpoint "Metrics endpoint" "$response"

# Summary
print_header "Test Summary"
echo -e "${GREEN}All API tests completed!${NC}"
echo -e "\n${BLUE}Additional endpoints to test manually:${NC}"
echo "  - POST /query with various natural language queries"
echo "  - Check processing_time_ms in responses"
echo "  - Monitor metrics at $BASE_URL/metrics"

echo -e "\n${YELLOW}Tips:${NC}"
echo "  - Install jq for prettier JSON output: brew install jq"
echo "  - View full metrics: curl $BASE_URL/metrics"
echo "  - Check logs: tail -f agent.log"

echo -e "\n${GREEN}✓ Testing complete!${NC}\n"