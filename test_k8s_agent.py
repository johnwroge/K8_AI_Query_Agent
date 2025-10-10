"""
Comprehensive test suite for Kubernetes AI Query Agent.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from kubernetes.client.rest import ApiException

from k8s_client import K8sClient
from ai_service import AIQueryService
from main import create_app


class TestK8sClient(unittest.TestCase):
    """Test cases for K8sClient."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_v1 = Mock()
        self.mock_apps_v1 = Mock()
    
    @patch('k8s_client.config.load_kube_config')
    @patch('k8s_client.k8s_client.CoreV1Api')
    @patch('k8s_client.k8s_client.AppsV1Api')
    def test_initialization_local(self, mock_apps, mock_core, mock_config):
        """Test local initialization of K8sClient."""
        client = K8sClient()
        
        mock_config.assert_called_once()
        mock_core.assert_called_once()
        mock_apps.assert_called_once()
        self.assertIsNotNone(client.v1)
        self.assertIsNotNone(client.apps_v1)
    
    @patch('k8s_client.k8s_client.CoreV1Api')
    def test_get_namespaces(self, mock_core):
        """Test getting namespaces."""
        # Create mock namespace objects
        mock_ns1 = Mock()
        mock_ns1.metadata.name = "default"
        mock_ns2 = Mock()
        mock_ns2.metadata.name = "kube-system"
        mock_ns3 = Mock()
        mock_ns3.metadata.name = "harbor"
        
        mock_list = Mock()
        mock_list.items = [mock_ns1, mock_ns2, mock_ns3]
        
        with patch('k8s_client.config.load_kube_config'):
            client = K8sClient()
            client.v1.list_namespace.return_value = mock_list
            
            # Test without filter
            namespaces = client.get_namespaces()
            self.assertEqual(len(namespaces), 3)
            self.assertIn("default", namespaces)
            
            # Test with filter
            filtered = client.get_namespaces(filter_pattern="harbor")
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0], "harbor")
    
    @patch('k8s_client.k8s_client.CoreV1Api')
    def test_get_pods(self, mock_core):
        """Test getting pod information."""
        # Create mock pod
        mock_pod = Mock()
        mock_pod.metadata.name = "test-pod"
        mock_pod.metadata.namespace = "default"
        mock_pod.status.phase = "Running"
        mock_pod.spec.node_name = "node-1"
        
        mock_container = Mock()
        mock_container.name = "nginx"
        mock_container.image = "nginx:latest"
        mock_container.ports = None
        
        mock_pod.spec.containers = [mock_container]
        
        mock_list = Mock()
        mock_list.items = [mock_pod]
        
        with patch('k8s_client.config.load_kube_config'):
            client = K8sClient()
            client.v1.list_namespaced_pod.return_value = mock_list
            
            pods = client.get_pods("default")
            
            self.assertEqual(len(pods), 1)
            self.assertEqual(pods[0]["name"], "test-pod")
            self.assertEqual(pods[0]["status"], "Running")
            self.assertEqual(len(pods[0]["containers"]), 1)
    
    @patch('k8s_client.k8s_client.CoreV1Api')
    def test_get_pods_api_exception(self, mock_core):
        """Test handling of API exceptions when getting pods."""
        with patch('k8s_client.config.load_kube_config'):
            client = K8sClient()
            client.v1.list_namespaced_pod.side_effect = ApiException("API Error")
            
            pods = client.get_pods("default")
            self.assertEqual(pods, [])
    
    @patch('k8s_client.k8s_client.CoreV1Api')
    def test_get_cluster_summary(self, mock_core):
        """Test getting comprehensive cluster summary."""
        with patch('k8s_client.config.load_kube_config'):
            client = K8sClient()
            
            # Mock all the list methods
            client.v1.list_namespaced_pod.return_value = Mock(items=[])
            client.v1.list_namespaced_service.return_value = Mock(items=[])
            client.v1.list_namespaced_secret.return_value = Mock(items=[])
            client.v1.list_namespaced_config_map.return_value = Mock(items=[])
            
            with patch.object(client, 'get_deployments', return_value=[]):
                summary = client.get_cluster_summary(["default"])
                
                self.assertIn("pods", summary)
                self.assertIn("services", summary)
                self.assertIn("secrets", summary)
                self.assertIn("configmaps", summary)
                self.assertIn("deployments", summary)


class TestAIQueryService(unittest.TestCase):
    """Test cases for AIQueryService."""
    
    @patch('ai_service.OpenAI')
    def test_initialization(self, mock_openai):
        """Test AIQueryService initialization."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock the validation call
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_client.chat.completions.create.return_value = mock_response
        
        service = AIQueryService()
        
        self.assertEqual(service.model, "gpt-3.5-turbo")
        self.assertEqual(service.temperature, 0)
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('ai_service.OpenAI')
    def test_query_success(self, mock_openai):
        """Test successful query processing."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock responses
        mock_validation = Mock()
        mock_validation.choices = [Mock()]
        
        mock_query = Mock()
        mock_message = Mock()
        mock_message.content = "5 pods are running"
        mock_query.choices = [Mock(message=mock_message)]
        
        mock_client.chat.completions.create.side_effect = [
            mock_validation,
            mock_query
        ]
        
        service = AIQueryService()
        cluster_data = {"pods": [{"name": "pod1"}, {"name": "pod2"}]}
        
        answer = service.query("How many pods?", cluster_data)
        
        self.assertEqual(answer, "5 pods are running")
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
    
    @patch('ai_service.OpenAI')
    def test_limit_cluster_data(self, mock_openai):
        """Test cluster data limiting functionality."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = Mock(choices=[Mock()])
        
        service = AIQueryService()
        
        large_data = {
            "pods": [{"name": f"pod-{i}"} for i in range(100)]
        }
        
        limited = service._limit_cluster_data(large_data, max_items_per_type=10)
        
        self.assertEqual(len(limited["pods"]), 10)


class TestFlaskApp(unittest.TestCase):
    """Test cases for Flask application."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_k8s = Mock(spec=K8sClient)
        self.mock_ai = Mock(spec=AIQueryService)
        
        self.app = create_app(
            k8s_client=self.mock_k8s,
            ai_service=self.mock_ai
        )
        self.client = self.app.test_client()
    
    def test_health_check_success(self):
        """Test successful health check."""
        self.mock_k8s.get_namespaces.return_value = ["default", "kube-system"]
        self.mock_ai.get_model_info.return_value = {"model": "gpt-3.5-turbo", "temperature": 0}
        
        response = self.client.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertIn("components", data)
    
    def test_health_check_failure(self):
        """Test health check when services are down."""
        self.mock_k8s.get_namespaces.side_effect = Exception("Connection failed")
        
        response = self.client.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 503)
        self.assertEqual(data["status"], "unhealthy")
    
    def test_query_success(self):
        """Test successful query processing."""
        self.mock_k8s.get_cluster_summary.return_value = {
            "pods": [{"name": "test-pod"}],
            "services": [],
            "secrets": [],
            "configmaps": [],
            "deployments": []
        }
        self.mock_ai.query.return_value = "1 pod is running"
        
        response = self.client.post(
            '/query',
            data=json.dumps({"query": "How many pods?"}),
            content_type='application/json'
        )
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["query"], "How many pods?")
        self.assertEqual(data["answer"], "1 pod is running")
        self.assertIn("processing_time_ms", data)
    
    def test_query_empty_body(self):
        """Test query with empty request body."""
        response = self.client.post('/query')
        
        self.assertEqual(response.status_code, 400)
    
    def test_query_invalid_query(self):
        """Test query with invalid/empty query string."""
        response = self.client.post(
            '/query',
            data=json.dumps({"query": ""}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_query_with_namespace(self):
        """Test query with specific namespace."""
        self.mock_k8s.get_cluster_summary.return_value = {
            "pods": [],
            "services": [],
            "secrets": [],
            "configmaps": [],
            "deployments": []
        }
        self.mock_ai.query.return_value = "No pods found"
        
        response = self.client.post(
            '/query',
            data=json.dumps({
                "query": "How many pods?",
                "namespace": "kube-system"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.mock_k8s.get_cluster_summary.assert_called_with(["kube-system"])
    
    def test_list_namespaces(self):
        """Test listing namespaces endpoint."""
        self.mock_k8s.get_namespaces.return_value = ["default", "kube-system", "harbor"]
        
        response = self.client.get('/namespaces')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["namespaces"]), 3)
        self.assertIn("default", data["namespaces"])
    
    def test_404_endpoint(self):
        """Test non-existent endpoint."""
        response = self.client.get('/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn("error", data)


class TestIntegration(unittest.TestCase):
    """Integration tests (require actual connections)."""
    
    @unittest.skip("Requires actual Kubernetes cluster and OpenAI API key")
    def test_full_query_flow(self):
        """Test complete query flow with real services."""
        app = create_app()
        client = app.test_client()
        
        response = client.post(
            '/query',
            data=json.dumps({"query": "How many nodes are in the cluster?"}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("answer", data)


if __name__ == '__main__':
    unittest.main()