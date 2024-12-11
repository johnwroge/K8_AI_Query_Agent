import requests
import time
import json

# List of test queries from your logs
test_queries = [
    "Which namespace is the harbor service deployed to?",
    "What is the name of the database in postgresql is harbor using?",
    "How many pods are in the cluster?",
    "What is the container port for harbor-core?",
    "What is the status of harbor registry?",
    "Which port will the harbor redis svc route traffic to?",
    "What is the rediness probe path for the harbor core?",
    "Which pod(s) associate with the harbor database secret",
    "What is the mount path of the persistent volume for the harbor database?",
    "What is the value of the environment variable CHART_CACHE_DRIVER in the harbor core pod?"
]

def test_query(query: str) -> None:
    """Send a single query to the API and print the response"""
    url = "http://localhost:8000/query"
    headers = {"Content-Type": "application/json"}
    data = {"query": query}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        result = response.json()
        print(f"\nQuery: {result['query']}")
        print(f"Answer: {result['answer']}")
        print("-" * 50)
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
    except json.JSONDecodeError:
        print("Error decoding response")

def run_all_tests() -> None:
    """Run through all test queries with a small delay between each"""
    print("Starting query tests...")
    print("=" * 50)
    
    for query in test_queries:
        test_query(query)
        time.sleep(1)  # Add a small delay between requests
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    run_all_tests()