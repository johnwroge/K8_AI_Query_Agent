import unittest
from unittest.mock import Mock, patch
from main import app

class TestK8sAgent(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_valid_query(self):
        response = self.app.post('/query', 
            json={"query": "How many nodes are in the cluster?"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('query', data)
        self.assertIn('answer', data)

    def test_invalid_query_format(self):
        response = self.app.post('/query', 
            json={"invalid": "format"})
        self.assertEqual(response.status_code, 400)

    @patch('main.get_k8s_info')
    def test_kubernetes_info_gathering(self, mock_get_k8s):
        mock_get_k8s.return_value = {
            "pods": [{"name": "nginx", "status": "Running"}],
            "nodes": [{"name": "minikube"}],
            "deployments": [{"name": "nginx"}]
        }
        response = self.app.post('/query', 
            json={"query": "What pods are running?"})
        self.assertEqual(response.status_code, 200)
    
    def test_pod_status_query(self):
        response = self.app.post('/query', 
            json={"query": "What is the status of the pod named 'example-pod'?"})
        self.assertEqual(response.status_code, 200)

    def test_deployment_pod_query(self):
        response = self.app.post('/query', 
            json={"query": "Which pod is spawned by my-deployment?"})
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()