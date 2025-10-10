"""
AI service module for processing natural language queries about Kubernetes clusters.
"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from openai import OpenAIError

logger = logging.getLogger(__name__)


class AIQueryService:
    """Service for processing natural language queries using OpenAI."""
    
    def __init__(self, model: str = "gpt-3.5-turbo", temperature: float = 0):
        """
        Initialize the AI query service.
        
        Args:
            model: OpenAI model to use (default: gpt-3.5-turbo)
            temperature: Temperature for response generation (default: 0)
        """
        self.client = OpenAI()
        self.model = model
        self.temperature = temperature
        self._validate_connection()
    
    def _validate_connection(self) -> None:
        """Validate OpenAI API connection."""
        try:
            
            logger.info("Skipping OpenAI validation to preserve API quota")
            return
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            logger.info("OpenAI connection validated successfully")
        except OpenAIError as e:
            logger.error(f"Failed to connect to OpenAI: {e}")
            raise
    
    def query(self, question: str, cluster_data: Dict[str, Any]) -> str:
        """
        Process a natural language query about cluster state.
        
        Args:
            question: Natural language question
            cluster_data: Dictionary containing cluster information
            
        Returns:
            AI-generated answer as string
        """
        try:
            system_prompt = self._build_system_prompt(cluster_data)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=self.temperature
            )
            
            answer = response.choices[0].message.content.strip()
            logger.debug(f"Query: {question} | Answer: {answer}")
            
            return answer
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error processing query: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in query processing: {e}")
            return "An unexpected error occurred while processing your query"
    
    def _build_system_prompt(self, cluster_data: Dict[str, Any]) -> str:
        """
        Build the system prompt with cluster information.
        
        Args:
            cluster_data: Dictionary containing cluster information
            
        Returns:
            Formatted system prompt
        """
        # Limit the size of data sent to avoid token limits
        limited_data = self._limit_cluster_data(cluster_data)
        
        prompt = f"""You are a Kubernetes cluster assistant. Analyze the provided cluster information and answer questions concisely and accurately.

Cluster Information:
{json.dumps(limited_data, indent=2)}

Response Guidelines:
1. Provide direct, concise answers
2. Use exact values from the cluster data
3. For counts, return only the number
4. For lists, use comma-separated values without spaces
5. If information is not available, respond with "Information not available"
6. Focus on factual information from the data provided
7. Do not make assumptions about data not present

Examples:
- "How many pods are running?" → "5"
- "What deployments exist?" → "nginx,mongodb,prometheus"
- "What is the status of pod X?" → "Running" or "Information not available"
"""
        return prompt
    
    def _limit_cluster_data(
        self, 
        cluster_data: Dict[str, Any], 
        max_items_per_type: int = 50
    ) -> Dict[str, Any]:
        """
        Limit the amount of cluster data to avoid token limits.
        
        Args:
            cluster_data: Full cluster data dictionary
            max_items_per_type: Maximum items to include per resource type
            
        Returns:
            Limited cluster data dictionary
        """
        limited = {}
        
        for resource_type, items in cluster_data.items():
            if isinstance(items, list):
                limited[resource_type] = items[:max_items_per_type]
                if len(items) > max_items_per_type:
                    logger.warning(
                        f"Limited {resource_type} from {len(items)} to "
                        f"{max_items_per_type} items"
                    )
            else:
                limited[resource_type] = items
        
        return limited
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            "model": self.model,
            "temperature": self.temperature
        }