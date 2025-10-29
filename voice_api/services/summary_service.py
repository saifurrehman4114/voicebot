"""
Summary and Context Service for generating conversation summaries and answering context questions
File: voice_api/services/summary_service.py
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger('voice_api')


class SummaryService:
    """Service to handle conversation summaries and context-based questions"""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    @staticmethod
    def generate_conversation_summary(messages, summary_type='all'):
        """
        Generate a summary of the conversation

        Args:
            messages: List or QuerySet of ChatMessage objects
            summary_type: 'first' for first message summary, 'all' for entire conversation

        Returns:
            tuple: (summary_text: str, error_message: str or None)
        """
        try:
            api_key = settings.GROQ_API_KEY
            if not api_key:
                return None, "Groq API key not configured"

            # Build the conversation text
            conversation_text = ""

            if summary_type == 'first':
                # Get only the first user message and bot response
                user_msgs = [msg for msg in messages if msg.message_type == 'user']
                bot_msgs = [msg for msg in messages if msg.message_type == 'bot']

                if user_msgs:
                    conversation_text += f"User: {user_msgs[0].transcribed_text}\n"
                if bot_msgs:
                    conversation_text += f"Bot: {bot_msgs[0].response_text}\n"
            else:
                # Get all messages
                for msg in messages:
                    if msg.message_type == 'user' and msg.transcribed_text:
                        conversation_text += f"User: {msg.transcribed_text}\n"
                    elif msg.message_type == 'bot' and msg.response_text:
                        conversation_text += f"Bot: {msg.response_text}\n"

            if not conversation_text:
                return "No messages to summarize", None

            # Prepare the summary request
            prompt = f"""Analyze the following conversation and provide a concise summary (2-3 sentences) highlighting:
1. The main topic or request
2. Key points discussed
3. Any action items or outcomes

Conversation:
{conversation_text}

Summary:"""

            payload = {
                "model": "llama-3.3-70b-versatile",  # Updated to current model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, informative summaries of conversations. Focus on the key points and actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.5,
                "max_tokens": 200,
                "top_p": 0.9
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                SummaryService.GROQ_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                summary = data['choices'][0]['message']['content'].strip()
                logger.info(f"Generated summary: {summary[:100]}...")
                return summary, None
            else:
                error_msg = f"Groq API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, error_msg

        except requests.RequestException as e:
            error_msg = f"Network error calling Groq API: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error in summary service: {str(e)}"
            logger.error(error_msg)
            return None, error_msg

    @staticmethod
    def answer_context_question(question, message_context, conversation_history, previous_context_questions=None):
        """
        Answer a question about a specific message in context

        Args:
            question: The user's question
            message_context: The specific message being asked about
            conversation_history: List of messages for full context
            previous_context_questions: Previous questions/answers about this message (optional)

        Returns:
            tuple: (answer_text: str, error_message: str or None)
        """
        try:
            api_key = settings.GROQ_API_KEY
            if not api_key:
                return None, "Groq API key not configured"

            # Build context from conversation
            context_text = ""
            for msg in conversation_history:
                if msg.message_type == 'user' and msg.transcribed_text:
                    context_text += f"User: {msg.transcribed_text}\n"
                elif msg.message_type == 'bot' and msg.response_text:
                    context_text += f"Bot: {msg.response_text}\n"

            # Identify the specific message
            if message_context.message_type == 'user':
                specific_message = f"User: {message_context.transcribed_text}"
                # Include entity information if available
                if message_context.intent:
                    specific_message += f"\nIntent: {message_context.intent}"
                if message_context.keywords:
                    specific_message += f"\nKeywords: {', '.join(message_context.keywords)}"
                if message_context.entities:
                    specific_message += f"\nEntities: {', '.join(message_context.entities)}"
            else:
                specific_message = f"Bot: {message_context.response_text}"

            # Build previous context questions text
            previous_qa_text = ""
            if previous_context_questions:
                for cq in previous_context_questions:
                    previous_qa_text += f"\nQ: {cq.question}\nA: {cq.answer}\n"

            # Prepare the question-answering request
            prompt = f"""Given the following conversation context, answer the user's question about a specific message.

Full Conversation:
{context_text}

Specific Message Being Asked About:
{specific_message}"""

            if previous_qa_text:
                prompt += f"""

Previous Questions/Responses About This Message:
{previous_qa_text}"""

            prompt += f"""

User's New Question: {question}

Please provide a clear, helpful answer based on all the above context (conversation history, the specific message details, and previous questions/responses):"""

            payload = {
                "model": "llama-3.3-70b-versatile",  # Updated to current model
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions about conversations. Provide clear, accurate answers based on the given context. If the context doesn't contain enough information to answer the question, say so politely."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.6,
                "max_tokens": 300,
                "top_p": 0.9
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                SummaryService.GROQ_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                answer = data['choices'][0]['message']['content'].strip()
                logger.info(f"Generated context answer: {answer[:100]}...")
                return answer, None
            else:
                error_msg = f"Groq API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return None, error_msg

        except requests.RequestException as e:
            error_msg = f"Network error calling Groq API: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error in context question service: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
