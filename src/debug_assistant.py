"""
Debug assistant module that combines pattern detection with AI analysis.
Provides actionable debugging insights for Kubernetes pod issues.
"""
import logging
import json
import os
from typing import Dict, List, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class DebugAssistant:
    """Assistant for analyzing and debugging Kubernetes pod crashes."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the debug assistant.
        
        Args:
            api_key: OpenAI API key (optional, defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  
    
    def detect_common_patterns(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect common crash patterns without AI (fast, deterministic).
        
        Args:
            analysis_data: Output from K8sAnalyzer.analyze_pod()
            
        Returns:
            Dictionary with detected patterns and preliminary diagnosis
        """
        pod_details = analysis_data.get("pod_details", {})
        events = analysis_data.get("events", [])
        current_logs = analysis_data.get("current_logs", "")
        previous_logs = analysis_data.get("previous_logs", "")
        
        patterns = {
            "detected_issues": [],
            "issue_type": None,
            "confidence": "unknown"
        }
        
        # Check container statuses
        container_statuses = pod_details.get("container_statuses", [])
        for cs in container_statuses:
            state = cs.get("state", {})
            last_state = cs.get("last_state", {})
            
            # CrashLoopBackOff detection
            if state.get("status") == "waiting" and state.get("reason") == "CrashLoopBackOff":
                patterns["detected_issues"].append("CrashLoopBackOff")
                patterns["issue_type"] = "CrashLoopBackOff"
                patterns["confidence"] = "high"
            
            # ImagePullBackOff / ErrImagePull
            if state.get("status") == "waiting":
                reason = state.get("reason", "")
                if "ImagePull" in reason or "ErrImage" in reason:
                    patterns["detected_issues"].append(f"Image pull error: {reason}")
                    patterns["issue_type"] = "ImagePullError"
                    patterns["confidence"] = "high"
            
            # OOMKilled detection
            if last_state and last_state.get("status") == "terminated":
                reason = last_state.get("reason", "")
                if reason == "OOMKilled":
                    patterns["detected_issues"].append("OOMKilled - Out of Memory")
                    patterns["issue_type"] = "OOMKilled"
                    patterns["confidence"] = "high"
                
                # Exit code analysis
                exit_code = last_state.get("exit_code")
                if exit_code and exit_code != 0:
                    patterns["detected_issues"].append(f"Container exited with code {exit_code}")
                    if not patterns["issue_type"]:
                        patterns["issue_type"] = f"ExitCode{exit_code}"
                        patterns["confidence"] = "medium"
        
        # Check events for additional clues
        for event in events:
            reason = event.get("reason", "")
            message = event.get("message", "")
            
            if "BackOff" in reason or "Back-off" in message:
                if "BackOff" not in str(patterns["detected_issues"]):
                    patterns["detected_issues"].append(f"Event: {reason}")
            
            if "Failed" in reason or "Error" in reason:
                patterns["detected_issues"].append(f"Event: {reason} - {message[:100]}")
        
        # Log analysis for common errors
        all_logs = previous_logs + "\n" + current_logs
        log_patterns = {
            "database": ["connection refused", "database", "postgres", "mysql", "mongodb", "redis"],
            "permission": ["permission denied", "forbidden", "unauthorized", "access denied"],
            "network": ["timeout", "connection reset", "connection refused", "no route to host"],
            "config": ["config", "configuration", "environment variable", "missing"],
        }
        
        for category, keywords in log_patterns.items():
            if any(keyword.lower() in all_logs.lower() for keyword in keywords):
                patterns["detected_issues"].append(f"Possible {category} issue in logs")
        
        return patterns
    
    def generate_debug_prompt(self, analysis_data: Dict[str, Any], patterns: Dict[str, Any]) -> str:
        """
        Generate a structured prompt for GPT-4 to analyze the pod crash.
        
        Args:
            analysis_data: Complete analysis data from K8sAnalyzer
            patterns: Detected patterns from pattern detection
            
        Returns:
            Formatted prompt string
        """
        pod_details = analysis_data.get("pod_details", {})
        
        prompt = f"""You are a Kubernetes debugging expert. Analyze this crashed/failing pod and provide actionable fixes.

POD INFORMATION:
- Name: {pod_details.get('name')}
- Namespace: {pod_details.get('namespace')}
- Phase: {pod_details.get('phase')}
- Node: {pod_details.get('node')}

CONTAINER STATUSES:
{json.dumps(pod_details.get('container_statuses', []), indent=2)}

DETECTED PATTERNS:
{json.dumps(patterns, indent=2)}

RECENT EVENTS (last 30 minutes):
{json.dumps(analysis_data.get('events', [])[:10], indent=2)}

PREVIOUS CONTAINER LOGS (from crash):
```
{analysis_data.get('previous_logs', 'No previous logs available')[:2000]}
```

CURRENT LOGS:
```
{analysis_data.get('current_logs', 'No current logs available')[:2000]}
```

TASK:
1. Identify the root cause of the issue
2. Explain what's happening in simple terms
3. Provide 3-5 specific, actionable fixes with exact kubectl commands

FORMAT YOUR RESPONSE AS JSON:
{{
  "root_cause": "Brief description of the root cause",
  "explanation": "Clear explanation of what's happening",
  "likely_causes": ["cause 1", "cause 2", "cause 3"],
  "suggested_fixes": [
    {{
      "action": "What to do",
      "command": "exact kubectl command",
      "why": "Why this might fix it"
    }}
  ],
  "severity": "critical|high|medium|low",
  "quick_fix_available": true|false
}}

Be specific, actionable, and practical. Focus on commands a developer can run RIGHT NOW."""
        
        return prompt
    
    def analyze_with_ai(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use GPT-4 to perform intelligent analysis of the pod crash.
        
        Args:
            analysis_data: Complete analysis data from K8sAnalyzer
            
        Returns:
            Structured debugging response with actionable fixes
        """
        logger.info("Starting AI analysis of pod crash")
        
        # First, detect common patterns (fast)
        patterns = self.detect_common_patterns(analysis_data)
        
        # Generate prompt for AI
        prompt = self.generate_debug_prompt(analysis_data, patterns)
        
        try:
            # Call GPT-4
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Kubernetes debugging expert. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent, focused responses
                max_tokens=2000
            )
            
            # Parse AI response
            ai_response_text = response.choices[0].message.content
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in ai_response_text:
                ai_response_text = ai_response_text.split("```json")[1].split("```")[0]
            elif "```" in ai_response_text:
                ai_response_text = ai_response_text.split("```")[1].split("```")[0]
            
            ai_analysis = json.loads(ai_response_text.strip())
            
            # Combine with pattern detection
            result = {
                "issue_type": patterns.get("issue_type", "Unknown"),
                "root_cause": ai_analysis.get("root_cause", "Unable to determine"),
                "explanation": ai_analysis.get("explanation", ""),
                "detected_patterns": patterns.get("detected_issues", []),
                "likely_causes": ai_analysis.get("likely_causes", []),
                "suggested_fixes": ai_analysis.get("suggested_fixes", []),
                "severity": ai_analysis.get("severity", "medium"),
                "quick_fix_available": ai_analysis.get("quick_fix_available", False),
                "confidence": patterns.get("confidence", "medium")
            }
            
            logger.info("AI analysis completed successfully")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Fallback response
            return self._create_fallback_response(patterns, analysis_data)
        
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            return self._create_fallback_response(patterns, analysis_data)
    
    def _create_fallback_response(
        self, 
        patterns: Dict[str, Any], 
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a fallback response when AI analysis fails.
        Uses pattern detection to provide basic debugging info.
        """
        pod_name = analysis_data.get("pod_details", {}).get("name", "unknown")
        namespace = analysis_data.get("pod_details", {}).get("namespace", "default")
        
        return {
            "issue_type": patterns.get("issue_type", "Unknown"),
            "root_cause": "AI analysis unavailable - using pattern detection",
            "explanation": f"Detected issues: {', '.join(patterns.get('detected_issues', ['No specific issues detected']))}",
            "detected_patterns": patterns.get("detected_issues", []),
            "likely_causes": [
                "Check container logs for error messages",
                "Verify resource limits and requests",
                "Check for configuration issues"
            ],
            "suggested_fixes": [
                {
                    "action": "View pod details",
                    "command": f"kubectl describe pod {pod_name} -n {namespace}",
                    "why": "Get comprehensive pod status and events"
                },
                {
                    "action": "Check container logs",
                    "command": f"kubectl logs {pod_name} -n {namespace}",
                    "why": "View application logs for errors"
                },
                {
                    "action": "Check previous logs if crashed",
                    "command": f"kubectl logs {pod_name} -n {namespace} --previous",
                    "why": "See logs from before the crash"
                }
            ],
            "severity": "medium",
            "quick_fix_available": False,
            "confidence": patterns.get("confidence", "low")
        }
    
    def debug_pod(self, pod_name: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Complete debugging workflow: analyze pod and provide fixes.
        This is the main entry point for pod debugging.
        
        Args:
            pod_name: Name of the pod to debug
            namespace: Kubernetes namespace
            
        Returns:
            Complete debugging response
        """
        from k8s_analyzer import K8sAnalyzer
        
        logger.info(f"Starting debug workflow for pod {pod_name}")
        
        # Initialize analyzer
        analyzer = K8sAnalyzer()
        
        # Gather analysis data
        analysis_data = analyzer.analyze_pod(pod_name, namespace)
        
        # Check if pod exists
        if not analysis_data.get("exists"):
            return {
                "success": False,
                "error": analysis_data.get("error"),
                "pod_name": pod_name,
                "namespace": namespace
            }
        
        # Perform AI analysis
        debug_result = self.analyze_with_ai(analysis_data)
        
        # Add metadata
        debug_result["pod_name"] = pod_name
        debug_result["namespace"] = namespace
        debug_result["success"] = True
        
        return debug_result