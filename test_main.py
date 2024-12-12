import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from main import create_app, K8sAssistant

class TestK8sAgent(unittest.TestCase):
    def setUp(self):
        self.app = create_app().test_client()
        self.app.testing = True

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "healthy"})

    def test_metrics_endpoint(self):
        """Test the metrics endpoint"""
        response = self.app.get('/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)  #

    @patch('main.K8sAssistant.get_k8s_info')
    @patch('main.K8sAssistant.query_gpt')
    def test_valid_query(self, mock_query_gpt, mock_get_k8s_info):
        """Test a valid query with mocked dependencies"""
        mock_get_k8s_info.return_value = {
            "pods": [{"name": "test-pod", "namespace": "default", "status": "Running"}],
            "services": [],
            "secrets": [],
            "configmaps": []
        }
        mock_query_gpt.return_value = "Test answer"

        response = self.app.post('/query', 
            json={"query": "How many pods are running?"},
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertIn('query', response_data)
        self.assertIn('answer', response_data)
        self.assertEqual(response_data['answer'], "Test answer")

    def test_invalid_query_format(self):
        """Test query with invalid JSON format"""
        response = self.app.post('/query', 
            json={}, 
            content_type='application/json')
        self.assertEqual(response.status_code, 500)  

    @patch('main.K8sAssistant.get_k8s_info')
    @patch('main.K8sAssistant.query_gpt')
    def test_query_with_complex_cluster_info(self, mock_query_gpt, mock_get_k8s_info):
        """Test query with a more complex cluster information"""
        mock_get_k8s_info.return_value = {
            "pods": [
                {
                    "name": "nginx-deployment-abc123",
                    "namespace": "default",
                    "status": "Running",
                    "containers": [
                        {
                            "name": "nginx",
                            "ports": [{"container_port": 80, "protocol": "TCP"}],
                            "env": [{"name": "ENV_VAR", "value": "test"}]
                        }
                    ]
                }
            ],
            "services": [
                {
                    "name": "nginx-service",
                    "namespace": "default",
                    "ports": [{"port": 80, "target_port": 80, "protocol": "TCP"}]
                }
            ],
            "secrets": [{"name": "nginx-secret", "namespace": "default"}],
            "configmaps": [{"name": "nginx-config", "namespace": "default", "data": {"key": "value"}}]
        }
        mock_query_gpt.return_value = "Detailed cluster information retrieved"

        response = self.app.post('/query', 
            json={"query": "Give me details about the cluster"},
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        response_data = response.get_json()
        self.assertEqual(response_data['answer'], "Detailed cluster information retrieved")

    def test_openai_connection_error(self):
        """Test scenario where OpenAI connection fails"""
        with patch('main.OpenAI', side_effect=Exception("OpenAI connection error")):
            app = create_app().test_client()
            
            response = app.post('/query', 
                json={"query": "Test query"},
                content_type='application/json')
            
            self.assertEqual(response.status_code, 500)
            error_data = response.get_json()
            self.assertIn('error', error_data)

if __name__ == '__main__':
    unittest.main()