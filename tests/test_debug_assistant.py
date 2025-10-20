"""
Test suite for the debug assistant functionality.
Tests both the analyzer and AI-powered debugging features.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.k8s_analyzer import K8sAnalyzer
from src.debug_assistant import DebugAssistant


class TestK8sAnalyzer:
    """Test cases for K8sAnalyzer."""
    
    @pytest.fixture
    def mock_k8s_client(self):
        """Mock Kubernetes API client."""
        with patch('src.k8s_analyzer.k8s_client') as mock_client, \
             patch('src.k8s_analyzer.config') as mock_config:
            yield mock_client, mock_config
    
    @pytest.fixture
    def analyzer(self, mock_k8s_client):
        """Create analyzer with mocked K8s client."""
        analyzer = K8sAnalyzer()
        return analyzer
    
    def test_extract_container_state_running(self, analyzer):
        """Test extracting running container state."""
        mock_state = Mock()
        mock_state.running = Mock()
        mock_state.running.started_at = datetime.now()
        mock_state.waiting = None
        mock_state.terminated = None
        
        result = analyzer._extract_container_state(mock_state)
        
        assert result["status"] == "running"
        assert "started_at" in result
    
    def test_extract_container_state_waiting(self, analyzer):
        """Test extracting waiting container state."""
        mock_state = Mock()
        mock_state.running = None
        mock_state.waiting = Mock()
        mock_state.waiting.reason = "CrashLoopBackOff"
        mock_state.waiting.message = "Back-off restarting failed container"
        mock_state.terminated = None
        
        result = analyzer._extract_container_state(mock_state)
        
        assert result["status"] == "waiting"
        assert result["reason"] == "CrashLoopBackOff"
        assert "Back-off" in result["message"]
    
    def test_extract_container_state_terminated(self, analyzer):
        """Test extracting terminated container state."""
        mock_state = Mock()
        mock_state.running = None
        mock_state.waiting = None
        mock_state.terminated = Mock()
        mock_state.terminated.exit_code = 1
        mock_state.terminated.reason = "Error"
        mock_state.terminated.message = "Container failed"
        mock_state.terminated.started_at = datetime.now()
        mock_state.terminated.finished_at = datetime.now()
        
        result = analyzer._extract_container_state(mock_state)
        
        assert result["status"] == "terminated"
        assert result["exit_code"] == 1
        assert result["reason"] == "Error"
    
    def test_get_pod_details_success(self, analyzer):
        """Test successful pod details retrieval."""
        # Mock pod object
        mock_pod = Mock()
        mock_pod.metadata.name = "test-pod"
        mock_pod.metadata.namespace = "default"
        mock_pod.metadata.creation_timestamp = datetime.now()
        mock_pod.status.phase = "Running"
        mock_pod.spec.node_name = "node-1"
        mock_pod.spec.restart_policy = "Always"
        
        # Mock container status
        mock_container_status = Mock()
        mock_container_status.name = "app"
        mock_container_status.ready = True
        mock_container_status.restart_count = 0
        mock_container_status.image = "nginx:latest"
        mock_container_status.state = Mock()
        mock_container_status.state.running = Mock()
        mock_container_status.state.running.started_at = datetime.now()
        mock_container_status.state.waiting = None
        mock_container_status.state.terminated = None
        mock_container_status.last_state = None
        
        mock_pod.status.container_statuses = [mock_container_status]
        mock_pod.status.conditions = []
        
        # Mock container spec
        mock_container = Mock()
        mock_container.name = "app"
        mock_container.env = []
        mock_container.resources = None
        mock_pod.spec.containers = [mock_container]
        
        analyzer.v1.read_namespaced_pod = Mock(return_value=mock_pod)
        
        result = analyzer.get_pod_details("test-pod", "default")
        
        assert result is not None
        assert result["name"] == "test-pod"
        assert result["namespace"] == "default"
        assert result["phase"] == "Running"
        assert len(result["container_statuses"]) == 1
    
    def test_get_pod_details_not_found(self, analyzer):
        """Test pod details when pod doesn't exist."""
        from kubernetes.client.rest import ApiException
        
        analyzer.v1.read_namespaced_pod = Mock(
            side_effect=ApiException(status=404, reason="Not Found")
        )
        
        result = analyzer.get_pod_details("nonexistent-pod", "default")
        
        assert result is None
    
    def test_get_pod_logs_success(self, analyzer):
        """Test successful log retrieval."""
        mock_logs = "Application starting...\nServer listening on port 8080"
        analyzer.v1.read_namespaced_pod_log = Mock(return_value=mock_logs)
        
        result = analyzer.get_pod_logs("test-pod", "default")
        
        assert result == mock_logs
        analyzer.v1.read_namespaced_pod_log.assert_called_once()
    
    def test_get_pod_events_success(self, analyzer):
        """Test successful event retrieval."""
        # Mock events
        mock_event = Mock()
        mock_event.involved_object.name = "test-pod"
        mock_event.involved_object.kind = "Pod"
        mock_event.last_timestamp = datetime.now()
        mock_event.first_timestamp = datetime.now()
        mock_event.type = "Warning"
        mock_event.reason = "BackOff"
        mock_event.message = "Back-off restarting failed container"
        mock_event.count = 5
        mock_event.source.component = "kubelet"
        
        mock_events = Mock()
        mock_events.items = [mock_event]
        
        analyzer.v1.list_namespaced_event = Mock(return_value=mock_events)
        
        result = analyzer.get_pod_events("test-pod", "default")
        
        assert len(result) == 1
        assert result[0]["reason"] == "BackOff"
        assert result[0]["type"] == "Warning"


class TestDebugAssistant:
    """Test cases for DebugAssistant."""
    
    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client."""
        with patch('src.debug_assistant.OpenAI') as mock:
            yield mock
    
    @pytest.fixture
    def assistant(self, mock_openai):
        """Create debug assistant with mocked OpenAI."""
        return DebugAssistant(api_key="test-key")
    
    def test_detect_crashloopbackoff(self, assistant):
        """Test detection of CrashLoopBackOff pattern."""
        analysis_data = {
            "pod_details": {
                "container_statuses": [
                    {
                        "name": "app",
                        "restart_count": 5,
                        "state": {
                            "status": "waiting",
                            "reason": "CrashLoopBackOff"
                        },
                        "last_state": {
                            "status": "terminated",
                            "exit_code": 1
                        }
                    }
                ]
            },
            "events": [],
            "current_logs": "",
            "previous_logs": ""
        }
        
        result = assistant.detect_common_patterns(analysis_data)
        
        assert "CrashLoopBackOff" in result["detected_issues"]
        assert result["issue_type"] == "CrashLoopBackOff"
        assert result["confidence"] == "high"
    
    def test_detect_oomkilled(self, assistant):
        """Test detection of OOMKilled pattern."""
        analysis_data = {
            "pod_details": {
                "container_statuses": [
                    {
                        "name": "app",
                        "restart_count": 3,
                        "state": {
                            "status": "running"
                        },
                        "last_state": {
                            "status": "terminated",
                            "exit_code": 137,
                            "reason": "OOMKilled"
                        }
                    }
                ]
            },
            "events": [],
            "current_logs": "",
            "previous_logs": ""
        }
        
        result = assistant.detect_common_patterns(analysis_data)
        
        assert any("OOMKilled" in issue for issue in result["detected_issues"])
        assert result["issue_type"] == "OOMKilled"
        assert result["confidence"] == "high"
    
    def test_detect_image_pull_error(self, assistant):
        """Test detection of image pull errors."""
        analysis_data = {
            "pod_details": {
                "container_statuses": [
                    {
                        "name": "app",
                        "restart_count": 0,
                        "state": {
                            "status": "waiting",
                            "reason": "ImagePullBackOff",
                            "message": "Back-off pulling image"
                        },
                        "last_state": None
                    }
                ]
            },
            "events": [],
            "current_logs": "",
            "previous_logs": ""
        }
        
        result = assistant.detect_common_patterns(analysis_data)
        
        assert result["issue_type"] == "ImagePullError"
        assert result["confidence"] == "high"
    
    def test_detect_database_issue_in_logs(self, assistant):
        """Test detection of database issues from logs."""
        analysis_data = {
            "pod_details": {
                "container_statuses": [
                    {
                        "name": "app",
                        "restart_count": 2,
                        "state": {"status": "running"},
                        "last_state": {
                            "status": "terminated",
                            "exit_code": 1
                        }
                    }
                ]
            },
            "events": [],
            "current_logs": "",
            "previous_logs": "ERROR: connection refused by postgres:5432\nDatabase connection failed"
        }
        
        result = assistant.detect_common_patterns(analysis_data)
        
        assert any("database" in issue.lower() for issue in result["detected_issues"])
    
    def test_generate_debug_prompt(self, assistant):
        """Test prompt generation for AI analysis."""
        analysis_data = {
            "pod_details": {
                "name": "test-pod",
                "namespace": "default",
                "phase": "CrashLoopBackOff",
                "node": "node-1",
                "container_statuses": [
                    {
                        "name": "app",
                        "restart_count": 5,
                        "state": {
                            "status": "waiting",
                            "reason": "CrashLoopBackOff"
                        }
                    }
                ]
            },
            "events": [
                {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "reason": "BackOff",
                    "message": "Back-off restarting failed container"
                }
            ],
            "previous_logs": "ERROR: Application failed to start",
            "current_logs": ""
        }
        
        patterns = {
            "detected_issues": ["CrashLoopBackOff"],
            "issue_type": "CrashLoopBackOff",
            "confidence": "high"
        }
        
        prompt = assistant.generate_debug_prompt(analysis_data, patterns)
        
        assert "test-pod" in prompt
        assert "CrashLoopBackOff" in prompt
        assert "BackOff" in prompt
        assert "kubectl" in prompt
    
    def test_create_fallback_response(self, assistant):
        """Test fallback response when AI fails."""
        patterns = {
            "detected_issues": ["CrashLoopBackOff", "Exit code 1"],
            "issue_type": "CrashLoopBackOff",
            "confidence": "high"
        }
        
        analysis_data = {
            "pod_details": {
                "name": "test-pod",
                "namespace": "default"
            }
        }
        
        result = assistant._create_fallback_response(patterns, analysis_data)
        
        assert result["issue_type"] == "CrashLoopBackOff"
        assert len(result["suggested_fixes"]) > 0
        assert all("kubectl" in fix["command"] for fix in result["suggested_fixes"])
        assert result["confidence"] == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])