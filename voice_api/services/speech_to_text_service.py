"""
AssemblyAI Speech-to-Text Service - OPTIMIZED FOR FREE TIER
File: voice_api/services/speech_to_text_service.py

Based on official AssemblyAI documentation research:
- Free tier: $50 credits = ~100 hours of transcription
- Best features available in free tier included
- Optimal parameters for voicebot use case
"""

import requests
import time
import os
from typing import Optional, Tuple
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """
    Production-ready Speech-to-Text service using AssemblyAI
    Optimized for free tier with best available features
    """
    
    def __init__(self):
        self.api_key = settings.ASSEMBLYAI_API_KEY
        self.base_url = "https://api.assemblyai.com"
        self.headers = {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
    
    def transcribe_audio(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Transcribe audio file using AssemblyAI with optimal settings
        
        Args:
            file_path: Path to audio file (any format: MP3, WAV, WebM, etc.)
            
        Returns:
            Tuple of (transcribed_text, error_message)
        """
        
        if not self.api_key:
            return None, "AssemblyAI API key not configured"
        
        try:
            # Step 1: Upload audio file
            logger.info(f"Uploading audio file: {file_path}")
            upload_url = self._upload_file(file_path)
            
            if not upload_url:
                return None, "Failed to upload audio file"
            
            # Step 2: Request transcription with optimal parameters
            logger.info(f"Requesting transcription for: {upload_url}")
            transcript_id = self._request_transcription(upload_url)
            
            if not transcript_id:
                return None, "Failed to start transcription"
            
            # Step 3: Poll for results
            logger.info(f"Polling for transcription results: {transcript_id}")
            transcribed_text, error = self._poll_transcription(transcript_id)
            
            if error:
                return None, error
            
            return transcribed_text, None
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return None, f"Transcription failed: {str(e)}"
    
    def _upload_file(self, file_path: str) -> Optional[str]:
        """Upload audio file to AssemblyAI"""
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    f"{self.base_url}/v2/upload",
                    headers=self.headers,
                    data=f,
                    timeout=300  # 5 minutes timeout for large files
                )
            
            if response.status_code == 200:
                upload_url = response.json().get('upload_url')
                logger.info(f"File uploaded successfully: {upload_url}")
                return upload_url
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return None
    
    def _request_transcription(self, audio_url: str) -> Optional[str]:
        """
        Request transcription from AssemblyAI with OPTIMAL FREE TIER PARAMETERS
        
        Based on official documentation research, these parameters are:
        1. FREE and available in free tier
        2. Best for voicebot/customer service use cases
        3. Improve accuracy and usability
        """
        try:
            # OPTIMIZED CONFIGURATION - All features are FREE
            data = {
                # Required parameter
                "audio_url": audio_url,
                
                # Language settings (FREE)
                "language_code": "en",  # or use "en_us" for US English specifically
                
                # Speaker identification (FREE) - CRITICAL for voicebots
                "speaker_labels": True,  # Identify different speakers
                
                # Text formatting (FREE) - Makes transcripts readable
                "format_text": True,  # Auto-capitalize and format properly
                
                # Filler words (FREE) - Keep "um", "uh" for natural conversation
                "disfluencies": True,  # Keep filler words for context
                
                # Filter profanity (FREE) - Good for customer service
                "filter_profanity": False,  # Set to True if you want to filter profanity
                
                # Punctuation (FREE) - Essential for readability
                "punctuate": True,  # Auto-add punctuation
                
                # Dual channel support (FREE) - If audio has separate channels
                "dual_channel": False,  # Set to True if you have stereo audio with different speakers
                
                # Audio quality threshold (FREE) - Reject poor audio
                "speech_threshold": 0.0,  # 0.0 = accept all, 0.5 = reject if <50% speech
            }
            
            response = requests.post(
                f"{self.base_url}/v2/transcript",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                transcript_id = response.json().get('id')
                logger.info(f"Transcription started: {transcript_id}")
                return transcript_id
            else:
                logger.error(f"Transcription request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Transcription request error: {str(e)}")
            return None
    
    def _poll_transcription(self, transcript_id: str, max_attempts: int = 60) -> Tuple[Optional[str], Optional[str]]:
        """
        Poll AssemblyAI for transcription results
        
        Args:
            transcript_id: Transcription ID
            max_attempts: Maximum polling attempts (default: 60 = 3 minutes)
        """
        polling_url = f"{self.base_url}/v2/transcript/{transcript_id}"
        attempts = 0
        
        while attempts < max_attempts:
            try:
                response = requests.get(
                    polling_url,
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"Polling failed: {response.status_code}")
                    return None, f"Polling failed with status {response.status_code}"
                
                result = response.json()
                status = result.get('status')
                
                if status == 'completed':
                    transcribed_text = result.get('text', '')
                    logger.info(f"Transcription completed: {len(transcribed_text)} characters")
                    
                    # Log speaker information if available
                    if result.get('utterances'):
                        num_speakers = len(set(u.get('speaker') for u in result.get('utterances', [])))
                        logger.info(f"Detected {num_speakers} speaker(s)")
                    
                    return transcribed_text, None
                    
                elif status == 'error':
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Transcription error: {error_msg}")
                    return None, f"Transcription error: {error_msg}"
                    
                else:
                    # Status is 'queued' or 'processing'
                    logger.info(f"Transcription status: {status} (attempt {attempts + 1}/{max_attempts})")
                    time.sleep(3)  # Wait 3 seconds before next poll
                    attempts += 1
                    
            except Exception as e:
                logger.error(f"Polling error: {str(e)}")
                return None, f"Polling error: {str(e)}"
        
        return None, "Transcription timed out after 3 minutes"


class SpeechToTextServiceAdvanced:
    """
    ADVANCED version with additional FREE features for specific use cases
    Use this if you need extra features like sentiment analysis, etc.
    """
    
    def __init__(self):
        self.api_key = settings.ASSEMBLYAI_API_KEY
        self.base_url = "https://api.assemblyai.com"
        self.headers = {
            "authorization": self.api_key,
            "content-type": "application/json"
        }
    
    def transcribe_with_intelligence(self, file_path: str) -> Tuple[Optional[dict], Optional[str]]:
        """
        Transcribe with additional Audio Intelligence features (FREE in trial)
        Returns full response with sentiment, entities, etc.
        """
        
        if not self.api_key:
            return None, "AssemblyAI API key not configured"
        
        try:
            # Upload file
            upload_url = self._upload_file(file_path)
            if not upload_url:
                return None, "Failed to upload audio file"
            
            # Request with Audio Intelligence features
            transcript_id = self._request_with_intelligence(upload_url)
            if not transcript_id:
                return None, "Failed to start transcription"
            
            # Poll for complete results
            result, error = self._poll_full_result(transcript_id)
            return result, error
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return None, f"Transcription failed: {str(e)}"
    
    def _upload_file(self, file_path: str) -> Optional[str]:
        """Upload audio file"""
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    f"{self.base_url}/v2/upload",
                    headers=self.headers,
                    data=f,
                    timeout=300
                )
            
            if response.status_code == 200:
                return response.json().get('upload_url')
            return None
        except Exception as e:
            logger.error(f"Upload error: {str(e)}")
            return None
    
    def _request_with_intelligence(self, audio_url: str) -> Optional[str]:
        """Request with Audio Intelligence features"""
        try:
            # FULL FEATURE SET - Most are FREE in trial period
            data = {
                "audio_url": audio_url,
                "language_code": "en",
                
                # Core features (FREE)
                "speaker_labels": True,
                "format_text": True,
                "punctuate": True,
                "disfluencies": True,
                
                # Audio Intelligence features (FREE in $50 credit)
                "sentiment_analysis": True,  # Detect positive/negative/neutral
                "entity_detection": True,    # Extract names, places, etc.
                "iab_categories": True,      # Topic/category detection
                
                # Advanced features (check if in free tier)
                # "auto_highlights": True,   # Extract key moments (may cost extra)
                # "summarization": True,     # Auto-summarize (may cost extra)
            }
            
            response = requests.post(
                f"{self.base_url}/v2/transcript",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('id')
            else:
                logger.error(f"Request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return None
    
    def _poll_full_result(self, transcript_id: str, max_attempts: int = 60) -> Tuple[Optional[dict], Optional[str]]:
        """Poll for complete results with all features"""
        polling_url = f"{self.base_url}/v2/transcript/{transcript_id}"
        attempts = 0
        
        while attempts < max_attempts:
            try:
                response = requests.get(polling_url, headers=self.headers, timeout=30)
                
                if response.status_code != 200:
                    return None, f"Polling failed with status {response.status_code}"
                
                result = response.json()
                status = result.get('status')
                
                if status == 'completed':
                    return result, None
                elif status == 'error':
                    return None, result.get('error', 'Unknown error')
                else:
                    time.sleep(3)
                    attempts += 1
                    
            except Exception as e:
                return None, f"Polling error: {str(e)}"
        
        return None, "Transcription timed out"


# USAGE EXAMPLES:
"""
# Basic usage (recommended for most cases):
from voice_api.services.speech_to_text_service import SpeechToTextService

service = SpeechToTextService()
text, error = service.transcribe_audio('path/to/audio.webm')

if error:
    print(f"Error: {error}")
else:
    print(f"Transcription: {text}")


# Advanced usage with Audio Intelligence:
from voice_api.services.speech_to_text_service import SpeechToTextServiceAdvanced

service = SpeechToTextServiceAdvanced()
result, error = service.transcribe_with_intelligence('path/to/audio.webm')

if error:
    print(f"Error: {error}")
else:
    print(f"Text: {result['text']}")
    print(f"Sentiment: {result.get('sentiment_analysis_results')}")
    print(f"Entities: {result.get('entities')}")
    print(f"Topics: {result.get('iab_categories_result')}")
"""