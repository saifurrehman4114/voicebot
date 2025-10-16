"""
Intent Classification Service using Groq API (FREE & FAST)
Compatible with Python 3.9
File: voice_api/services/intent_classifier_service.py
"""

import requests
from django.conf import settings
from typing import Tuple, Optional
import json
import os


class IntentClassifierService:
    """Service for classifying intent using Groq API (Free & Fast)"""
    
    def __init__(self):
        self.api_key = os.environ.get('GROQ_API_KEY', '')
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def classify_intent(self, text: str) -> Tuple[str, float, str, Optional[str]]:
        """
        Classify intent using Groq API
        
        Returns:
            Tuple of (intent, confidence, summary, error_message)
        """
        
        if not self.api_key:
            return 'unknown_intent', 0.0, text[:100], "Groq API key not configured"
        
        prompt = f"""Analyze this voice message and classify the intent.

Transcription: "{text}"

Provide:
1. Specific intent (e.g., "screen_replacement", "battery_issue", "pricing_inquiry")
2. Confidence score (0.0-1.0)
3. Brief summary (1-2 sentences)

Respond ONLY with JSON:
{{
    "intent": "category_name",
    "confidence": 0.95,
    "summary": "description"
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
                "max_tokens": 200
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                return 'unknown_intent', 0.0, text[:100], f"API error: {response.status_code}"
            
            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()
            
            # Clean response
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(response_text)
            
            intent = result.get('intent', 'unknown_intent')
            confidence = float(result.get('confidence', 0.5))
            summary = result.get('summary', text[:100])
            
            return intent, confidence, summary, None
            
        except requests.exceptions.Timeout:
            return 'unknown_intent', 0.0, text[:100], "Request timed out"
        except Exception as e:
            return 'unknown_intent', 0.0, text[:100], f"Error: {str(e)}"