# K8s Debug Assistant - Quick Reference

## Setup

```bash
# Set OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env

# Start services
minikube start
python run.py
```

## Core Commands

### Debug a Pod

```bash
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "YOUR_POD_NAME", "namespace": "default"}' | jq
```

### Debug Script

```bash
#!/bin/bash
# Save as: debug-pod.sh
POD_NAME=$1
NAMESPACE=${2:-default}

curl -s -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d "{\"pod_name\": \"$POD_NAME\", \"namespace\": \"$NAMESPACE\"}" | jq
```

Usage:
```bash
chmod +x debug-pod.sh
./debug-pod.sh my-app-pod production
```

### Health Check

```bash
curl http://localhost:8000/health | jq
```

## Detected Issue Types

| Issue Type | Description | Typical Fix |
|------------|-------------|-------------|
| CrashLoopBackOff | Container repeatedly crashes | Check logs for errors |
| ImagePullBackOff | Cannot pull container image | Verify image name and credentials |
| OOMKilled | Out of memory | Increase memory limits |
| Exit Code 1 | Application error | Review application logs |
| Config Errors | Missing environment variables | Add required configuration |
| Network Issues | Cannot reach services | Check service availability and DNS |

## Response Format

```json
{
  "success": true,
  "issue_type": "CrashLoopBackOff",
  "root_cause": "Brief description",
  "likely_causes": ["cause1", "cause2"],
  "suggested_fixes": [
    {
      "action": "What to do",
      "command": "kubectl command to run",
      "why": "Why this helps"
    }
  ],
  "severity": "high",
  "processing_time_ms": 2347
}
```

## Common Workflow

```bash
# Find failing pods
kubectl get pods | grep -E 'Error|CrashLoop|ImagePull|OOM'

# Debug a specific pod
POD_NAME="my-app-xyz"
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d "{\"pod_name\": \"$POD_NAME\"}" | jq

# Execute suggested commands
kubectl logs $POD_NAME --previous
kubectl describe pod $POD_NAME

# Apply fixes and redeploy
```

## Testing

```bash
# Deploy test pods
kubectl apply -f deployment/test-broken-pods.yaml

# Debug each scenario
curl -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "crash-loop-test"}' | jq

# Cleanup
kubectl delete -f deployment/test-broken-pods.yaml
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "OpenAI API key required" | Set `OPENAI_API_KEY` environment variable |
| "Failed to initialize K8s" | Ensure Minikube is running: `minikube start` |
| Import errors | Verify `conftest.py` exists in project root |
| Slow response | Check OpenAI API status and network |
| Pod not found | Verify pod name: `kubectl get pods` |

## Cost Information

**Pattern Detection:** Free and instantaneous
- CrashLoopBackOff
- OOMKilled
- ImagePullBackOff
- Common exit codes

**AI Analysis:** Approximately $0.0006 per request
- Uses GPT-4o-mini
- Only invoked for complex cases
- Pattern detection runs first

## Monitoring

```bash
# View all metrics
curl http://localhost:8000/metrics

# Debug request count
curl -s http://localhost:8000/metrics | grep k8s_agent_debug_requests_total

# Response times
curl -s http://localhost:8000/metrics | grep k8s_agent_debug_duration
```

## Advanced Usage

### Create Bash Alias

```bash
alias debug='curl -s -X POST http://localhost:8000/debug/pod-crash -H "Content-Type: application/json" -d "{\"pod_name\": \"$1\"}" | jq'
```

Usage: `debug my-pod-name`

### Save Debug Reports

```bash
curl -s -X POST http://localhost:8000/debug/pod-crash \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "my-pod"}' > debug-$(date +%Y%m%d-%H%M%S).json
```


### Debug Multiple Failing Pods

```bash
# Get all non-running pods
kubectl get pods --field-selector=status.phase!=Running -o jsonpath='{.items[*].metadata.name}'

# Debug each one
for pod in $(kubectl get pods --field-selector=status.phase!=Running -o jsonpath='{.items[*].metadata.name}'); do
  echo "=== Debugging: $pod ==="
  curl -s -X POST http://localhost:8000/debug/pod-crash \
    -H "Content-Type: application/json" \
    -d "{\"pod_name\": \"$pod\"}" | jq -r '.root_cause, .issue_type'
  echo ""
done
```

Or save full reports:
```bash
# Debug all failing pods and save to files
for pod in $(kubectl get pods --field-selector=status.phase!=Running -o jsonpath='{.items[*].metadata.name}'); do
  curl -s -X POST http://localhost:8000/debug/pod-crash \
    -H "Content-Type: application/json" \
    -d "{\"pod_name\": \"$pod\"}" > "debug-$pod-$(date +%Y%m%d).json"
  echo "Saved: debug-$pod-$(date +%Y%m%d).json"
done
```


## Additional Resources

- Check application logs: `tail -f agent.log`
- Run test suite: `pytest -v`
- View full README: `README.md`

**Note:** This tool provides diagnostic information and suggested commands. You must execute the recommended kubectl commands manually to resolve issues.