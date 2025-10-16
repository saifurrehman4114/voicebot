"""
Entity and Key Terms Extraction Service
File: voice_api/services/entity_extraction_service.py
"""

import requests
from typing import List, Dict, Optional, Tuple
import json
import os


class EntityExtractionService:
    """Service for extracting key terms, entities, and important concepts from text"""
    
    def __init__(self):
        self.api_key = os.environ.get('GROQ_API_KEY', '')
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def extract_entities(self, text: str) -> Tuple[Dict, Optional[str]]:
        """
        Extract key entities, terms, and concepts from transcribed text
        
        Returns:
            Tuple of (entities_dict, error_message)
            
        entities_dict contains:
            - keywords: List of important single words/phrases
            - entities: Named entities (people, places, organizations, etc.)
            - medical_terms: Domain-specific terms (if medical context)
            - technical_terms: Technical/specialized terms
            - action_items: Things that need to be done
            - topics: Main subjects/themes discussed
        """
        
        if not self.api_key:
            return {
                'keywords': [],
                'entities': [],
                'domain_terms': [],
                'action_items': [],
                'topics': []
            }, "API key not configured"
        
        prompt = f"""Analyze this transcription and extract key information.

Transcription: "{text}"

Extract and categorize:
1. **keywords**: Most important 5-10 words/short phrases that capture the essence
2. **entities**: Named entities (people, places, organizations, products, etc.)
3. **domain_terms**: Specialized/technical terms specific to the domain (medical, legal, technical, etc.)
4. **action_items**: Any tasks, requests, or things that need to be done
5. **topics**: Main subjects or themes being discussed (2-4 topics)

Respond ONLY with valid JSON:
{{
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "entities": ["entity1", "entity2"],
    "domain_terms": ["term1", "term2"],
    "action_items": ["action1", "action2"],
    "topics": ["topic1", "topic2"]
}}"""

        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            }
            
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                return self._empty_result(), f"API error: {response.status_code}"
            
            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()
            
            # Clean response
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(response_text)
            
            # Ensure all fields exist
            entities = {
                'keywords': result.get('keywords', []),
                'entities': result.get('entities', []),
                'domain_terms': result.get('domain_terms', []),
                'action_items': result.get('action_items', []),
                'topics': result.get('topics', [])
            }
            
            return entities, None
            
        except Exception as e:
            return self._empty_result(), f"Error: {str(e)}"
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'keywords': [],
            'entities': [],
            'domain_terms': [],
            'action_items': [],
            'topics': []
        }