"""
Chat Service for context-aware conversation using Groq API
File: voice_api/services/chat_service.py
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger('voice_api')


class ChatService:
    """Service to handle context-aware chat responses using Groq API"""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    @staticmethod
    def generate_response(conversation_history, current_message):
        """
        Generate a context-aware response using Groq API

        Args:
            conversation_history: List of previous messages in conversation
                                 Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
            current_message: The current user message (transcribed text)

        Returns:
            tuple: (response_text: str, error_message: str or None)
        """
        try:
            api_key = settings.GROQ_API_KEY

            if not api_key:
                return None, "Groq API key not configured"

            # Build the conversation context
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful and friendly AI assistant in a voice chat conversation. "
                        "The user is communicating with you via voice messages. "
                        "Provide concise, natural, and conversational responses. "
                        "Keep your responses brief (2-3 sentences) as they will be read as text messages. "
                        "Be warm, empathetic, and helpful. Remember the context of the conversation."
                    )
                }
            ]

            # Add conversation history (limit to last 10 messages to manage token usage)
            for msg in conversation_history[-10:]:
                messages.append(msg)

            # Add the current message
            messages.append({
                "role": "user",
                "content": current_message
            })

            # Prepare request
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.7,  # More creative for conversation
                "max_tokens": 150,    # Keep responses concise
                "top_p": 0.9
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # Make request to Groq
            response = requests.post(
                ChatService.GROQ_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data['choices'][0]['message']['content'].strip()
                logger.info(f"Generated chat response: {response_text[:100]}...")
                return response_text, None
            else:
                error_msg = f"Groq API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, error_msg

        except requests.RequestException as e:
            error_msg = f"Network error calling Groq API: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error in chat service: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def build_conversation_history(chat_messages):
        """
        Build conversation history from ChatMessage objects

        Args:
            chat_messages: QuerySet of ChatMessage objects ordered by created_at

        Returns:
            List of message dictionaries for Groq API
        """
        history = []

        for msg in chat_messages:
            if msg.message_type == 'user' and msg.transcribed_text:
                history.append({
                    "role": "user",
                    "content": msg.transcribed_text
                })
            elif msg.message_type == 'bot' and msg.response_text:
                history.append({
                    "role": "assistant",
                    "content": msg.response_text
                })

        return history
