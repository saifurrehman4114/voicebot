"""
Updated API Views with entity extraction
File: voice_api/views.py
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.utils import timezone
import os
import logging

from .models import VoiceRequest, PhoneVerification, ChatConversation, ChatMessage, ContextQuestion
from .serializers import (
    VoiceRequestSerializer, VoiceUploadSerializer,
    SendOTPSerializer, VerifyOTPSerializer, PhoneVerificationSerializer,
    ChatMessageSerializer, ChatConversationSerializer, SendChatMessageSerializer
)
from .services.speech_to_text_service import SpeechToTextService
from .services.intent_classifier_service import IntentClassifierService
from .services.entity_extraction_service import EntityExtractionService
from .services.otp_service import OTPService
from .services.chat_service import ChatService
from .services.summary_service import SummaryService

logger = logging.getLogger(__name__)


class VoiceUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        logger.info(f"Received upload request")
        serializer = VoiceUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"Validation errors: {serializer.errors}")
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        audio_file = serializer.validated_data['audio_file']
        
        voice_request = VoiceRequest.objects.create(
            file_size=audio_file.size,
            file_format=audio_file.name.split('.')[-1],
            status='processing',
            user_ip=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        try:
            # Save audio file
            file_path = self.save_audio_file(audio_file, voice_request.id)
            voice_request.audio_file = file_path
            voice_request.save()
            
            # Step 1: Transcribe audio to text
            speech_service = SpeechToTextService()
            transcribed_text, error = speech_service.transcribe_audio(file_path)
            
            if error:
                voice_request.status = 'failed'
                voice_request.error_message = error
                voice_request.save()
                return Response(
                    {'id': str(voice_request.id), 'status': 'failed', 'error': error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            voice_request.transcribed_text = transcribed_text
            voice_request.save()
            
            # Step 2: Classify intent
            intent_service = IntentClassifierService()
            intent, confidence, summary, error = intent_service.classify_intent(transcribed_text)
            
            if error:
                logger.warning(f"Intent classification warning: {error}")
            
            voice_request.intent = intent
            voice_request.intent_confidence = confidence
            voice_request.intent_summary = summary
            
            # Step 3: Extract entities and key terms (NEW)
            entity_service = EntityExtractionService()
            entities, error = entity_service.extract_entities(transcribed_text)
            
            if error:
                logger.warning(f"Entity extraction warning: {error}")
            else:
                voice_request.keywords = entities.get('keywords', [])
                voice_request.entities = entities.get('entities', [])
                voice_request.domain_terms = entities.get('domain_terms', [])
                voice_request.action_items = entities.get('action_items', [])
                voice_request.topics = entities.get('topics', [])
            
            # Mark as completed
            voice_request.status = 'completed'
            voice_request.processed_at = timezone.now()
            voice_request.save()
            
            response_serializer = VoiceRequestSerializer(voice_request)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error processing voice request: {str(e)}")
            voice_request.status = 'failed'
            voice_request.error_message = str(e)
            voice_request.save()
            return Response(
                {'id': str(voice_request.id), 'status': 'failed', 'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def save_audio_file(self, audio_file, request_id):
        os.makedirs(settings.VOICE_FILES_DIR, exist_ok=True)
        file_extension = audio_file.name.split('.')[-1]
        filename = f"{request_id}.{file_extension}"
        file_path = os.path.join(settings.VOICE_FILES_DIR, filename)
        
        with open(file_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        return file_path
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VoiceRequestDetailView(APIView):
    def get(self, request, request_id):
        try:
            voice_request = VoiceRequest.objects.get(id=request_id)
            serializer = VoiceRequestSerializer(voice_request)
            return Response(serializer.data)
        except VoiceRequest.DoesNotExist:
            return Response({'error': 'Voice request not found'}, status=status.HTTP_404_NOT_FOUND)


class VoiceRequestListView(APIView):
    def get(self, request):
        queryset = VoiceRequest.objects.all()
        
        # Existing filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        intent_filter = request.query_params.get('intent')
        if intent_filter:
            queryset = queryset.filter(intent=intent_filter)
        
        # NEW: Search by keyword
        keyword_filter = request.query_params.get('keyword')
        if keyword_filter:
            queryset = queryset.filter(keywords__contains=[keyword_filter])
        
        # NEW: Search by topic
        topic_filter = request.query_params.get('topic')
        if topic_filter:
            queryset = queryset.filter(topics__contains=[topic_filter])
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = queryset.count()
        voice_requests = queryset[start:end]
        
        serializer = VoiceRequestSerializer(voice_requests, many=True)
        
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })


# ==================== OTP VERIFICATION VIEWS ====================

class SendOTPView(APIView):
    """Send OTP code to phone number"""

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = OTPService.format_email(serializer.validated_data['email'])

        # Generate OTP
        otp_code = OTPService.generate_otp()

        # Send OTP via email
        success, message, message_id = OTPService.send_otp(email, otp_code)

        if not success:
            logger.error(f"Failed to send OTP to {email}: {message}")
            return Response(
                {'error': message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Store OTP in database (using phone_number field for backward compatibility)
        phone_verification = PhoneVerification.objects.create(
            phone_number=email,
            otp_code=otp_code,
            expires_at=OTPService.get_otp_expiration()
        )

        logger.info(f"OTP created for {email}")

        # Build response
        response_data = {
            'message': message,
            'email': email,
            'expires_in_minutes': 10
        }

        # In DEBUG mode, also return OTP for easy testing
        if settings.DEBUG:
            response_data['otp_code'] = otp_code
            response_data['dev_mode'] = True
            logger.warning(f"🔐 DEV MODE - OTP Code for {email}: {otp_code}")

        return Response(response_data, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """Verify OTP code and create session"""

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        email = OTPService.format_email(serializer.validated_data['email'])
        otp_code = serializer.validated_data['otp_code']

        try:
            # Find the most recent OTP for this email
            phone_verification = PhoneVerification.objects.filter(
                phone_number=email,
                is_verified=False
            ).order_by('-created_at').first()

            if not phone_verification:
                return Response(
                    {'error': 'No OTP found for this email. Please request a new OTP.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if OTP has expired
            if OTPService.is_otp_expired(phone_verification.expires_at):
                return Response(
                    {'error': 'OTP has expired. Please request a new OTP.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check attempts limit
            if phone_verification.verification_attempts >= 3:
                return Response(
                    {'error': 'Too many failed attempts. Please request a new OTP.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify OTP code
            if phone_verification.otp_code != otp_code:
                phone_verification.verification_attempts += 1
                phone_verification.save()

                return Response(
                    {
                        'error': 'Invalid OTP code',
                        'attempts_remaining': 3 - phone_verification.verification_attempts
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # OTP is valid - mark as verified
            phone_verification.is_verified = True
            phone_verification.verified_at = timezone.now()
            phone_verification.save()

            # Check if user has any conversations, create one if not
            conversation = ChatConversation.objects.filter(
                phone_number=email
            ).first()

            if not conversation:
                conversation = ChatConversation.objects.create(
                    phone_number=email,
                    title="New Chat"
                )

            # Create session
            request.session['phone_number'] = email
            request.session['user_email'] = email  # Add this for calendar views
            request.session['verified'] = True
            request.session['conversation_id'] = str(conversation.id)

            logger.info(f"Successfully verified OTP for {email}")

            return Response({
                'message': 'OTP verified successfully',
                'email': email,
                'conversation_id': str(conversation.id)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error verifying OTP: {str(e)}")
            return Response(
                {'error': 'An error occurred during verification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CheckSessionView(APIView):
    """Check if user has active session"""

    def get(self, request):
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if phone_number and verified:
            return Response({
                'authenticated': True,
                'phone_number': phone_number,
                'email': phone_number  # Backward compatibility
            })
        else:
            return Response({
                'authenticated': False
            })


class LogoutView(APIView):
    """Logout user by clearing session"""

    def post(self, request):
        request.session.flush()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


# ==================== CHAT VIEWS ====================

class SendChatMessageView(APIView):
    """Send audio message in chat and get AI response"""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        # Check session
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated. Please verify your phone number.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = SendChatMessageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        audio_file = serializer.validated_data['audio_file']

        try:
            # Get conversation
            conversation = ChatConversation.objects.get(phone_number=phone_number)

            # Save audio file
            file_path = self.save_audio_file(audio_file, conversation.id)

            # Transcribe audio
            speech_service = SpeechToTextService()
            transcribed_text, error = speech_service.transcribe_audio(file_path)

            if error:
                return Response(
                    {'error': f'Transcription failed: {error}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract entities and classify intent
            entity_service = EntityExtractionService()
            intent_service = IntentClassifierService()

            # Get intent
            intent, confidence, summary, intent_error = intent_service.classify_intent(transcribed_text)

            # Get entities
            entities_data, entity_error = entity_service.extract_entities(transcribed_text)

            # Create user message with entity data
            user_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='user',
                audio_file=file_path,
                transcribed_text=transcribed_text,
                intent=intent if not intent_error else None,
                keywords=entities_data.get('keywords', []) if not entity_error else [],
                entities=entities_data.get('entities', []) if not entity_error else [],
                domain_terms=entities_data.get('domain_terms', []) if not entity_error else [],
                action_items=entities_data.get('action_items', []) if not entity_error else [],
                topics=entities_data.get('topics', []) if not entity_error else []
            )

            # Build conversation history
            previous_messages = ChatMessage.objects.filter(
                conversation=conversation
            ).order_by('created_at')

            chat_service = ChatService()
            conversation_history = chat_service.build_conversation_history(previous_messages)

            # Generate AI response
            response_text, error = chat_service.generate_response(
                conversation_history,
                transcribed_text
            )

            if error:
                logger.error(f"Chat response error: {error}")
                response_text = "I'm sorry, I'm having trouble responding right now. Please try again."

            # Create bot message
            bot_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='bot',
                response_text=response_text
            )

            # Update conversation metadata
            conversation.total_messages += 2
            conversation.save()

            # Return both messages
            return Response({
                'user_message': ChatMessageSerializer(user_message, context={'request': request}).data,
                'bot_message': ChatMessageSerializer(bot_message, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)

        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending chat message: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your message'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def save_audio_file(self, audio_file, conversation_id):
        """Save audio file to media directory"""
        import uuid
        os.makedirs(settings.VOICE_FILES_DIR, exist_ok=True)
        file_extension = audio_file.name.split('.')[-1]
        filename = f"chat_{conversation_id}_{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.VOICE_FILES_DIR, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        return file_path


class ChatHistoryView(APIView):
    """Get conversation history"""

    def get(self, request):
        # Check session
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated. Please verify your phone number.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            conversation = ChatConversation.objects.get(phone_number=phone_number)
            messages = ChatMessage.objects.filter(
                conversation=conversation
            ).order_by('created_at')

            serializer = ChatMessageSerializer(messages, many=True, context={'request': request})

            return Response({
                'conversation_id': str(conversation.id),
                'phone_number': phone_number,
                'total_messages': conversation.total_messages,
                'messages': serializer.data
            })

        except ChatConversation.DoesNotExist:
            return Response({
                'conversation_id': None,
                'phone_number': phone_number,
                'total_messages': 0,
                'messages': []
            })


# ==================== NEW CHAT VIEWS FOR MODERN UI ====================

class ConversationsListView(APIView):
    """Get all conversations for the current user"""

    def get(self, request):
        # Check session
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        conversations = ChatConversation.objects.filter(
            phone_number=phone_number
        ).order_by('-last_activity')

        serializer = ChatConversationSerializer(conversations, many=True)

        return Response({
            'conversations': serializer.data
        })


class ConversationDetailView(APIView):
    """Get specific conversation with messages"""

    def get(self, request, conversation_id):
        # Check session
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id,
                phone_number=phone_number
            )

            messages = ChatMessage.objects.filter(
                conversation=conversation
            ).order_by('created_at')

            message_serializer = ChatMessageSerializer(messages, many=True, context={'request': request})

            return Response({
                'id': str(conversation.id),
                'title': conversation.title,
                'total_messages': conversation.total_messages,
                'last_activity': conversation.last_activity,
                'created_at': conversation.created_at,
                'messages': message_serializer.data
            })

        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, conversation_id):
        """Delete a conversation"""
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id,
                phone_number=phone_number
            )
            conversation.delete()

            return Response(
                {'message': 'Conversation deleted successfully'},
                status=status.HTTP_200_OK
            )

        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class NewConversationView(APIView):
    """Create a new conversation"""

    def post(self, request):
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Create new conversation
        conversation = ChatConversation.objects.create(
            phone_number=phone_number,
            title="New Chat"
        )

        return Response({
            'conversation_id': str(conversation.id),
            'title': conversation.title,
            'message': 'New conversation created'
        }, status=status.HTTP_201_CREATED)


class SendChatMessageModernView(APIView):
    """Enhanced chat message with conversation support"""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        # Check session
        phone_number = request.session.get('phone_number')
        verified = request.session.get('verified', False)

        if not phone_number or not verified:
            return Response(
                {'error': 'Not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = SendChatMessageSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        audio_file = serializer.validated_data.get('audio_file')
        attachment_file = serializer.validated_data.get('attachment_file')
        conversation_id = request.data.get('conversation_id')

        try:
            # Get or create conversation
            if conversation_id:
                conversation = ChatConversation.objects.get(
                    id=conversation_id,
                    phone_number=phone_number
                )
            else:
                # Create new conversation if none specified
                conversation = ChatConversation.objects.create(
                    phone_number=phone_number,
                    title="New Chat"
                )

            # Save audio file if provided
            file_path = None
            transcribed_text = ""

            if audio_file:
                file_path = self.save_audio_file(audio_file, conversation.id)

                # Transcribe audio
                speech_service = SpeechToTextService()
                transcribed_text, error = speech_service.transcribe_audio(file_path)

                if error:
                    return Response(
                        {'error': f'Transcription failed: {error}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Save attachment file if provided
            attachment_path = None
            attachment_type = None
            attachment_name = None
            attachment_size = None

            if attachment_file:
                attachment_path, attachment_type = self.save_attachment_file(attachment_file, conversation.id)
                attachment_name = attachment_file.name
                attachment_size = attachment_file.size

            # Extract entities and classify intent (only if we have transcribed text)
            intent = None
            entities_data = {}

            if transcribed_text:
                entity_service = EntityExtractionService()
                intent_service = IntentClassifierService()

                # Get intent
                intent, confidence, summary, intent_error = intent_service.classify_intent(transcribed_text)

                # Get entities
                entities_data, entity_error = entity_service.extract_entities(transcribed_text)

            # Create user message with entity data and attachment
            user_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='user',
                audio_file=file_path,
                transcribed_text=transcribed_text,
                attachment_file=attachment_path,
                attachment_type=attachment_type,
                attachment_name=attachment_name,
                attachment_size=attachment_size,
                intent=intent if intent else None,
                keywords=entities_data.get('keywords', []) if entities_data else [],
                entities=entities_data.get('entities', []) if entities_data else [],
                domain_terms=entities_data.get('domain_terms', []) if entities_data else [],
                action_items=entities_data.get('action_items', []) if entities_data else [],
                topics=entities_data.get('topics', []) if entities_data else []
            )

            # Generate conversation title from first message
            if conversation.total_messages == 0:
                if transcribed_text:
                    conversation.title = self.generate_title(transcribed_text)
                elif attachment_name:
                    conversation.title = f"Attachment: {attachment_name[:30]}..."
                else:
                    conversation.title = "New Chat"

            # Build conversation history
            previous_messages = ChatMessage.objects.filter(
                conversation=conversation
            ).order_by('created_at')

            chat_service = ChatService()
            conversation_history = chat_service.build_conversation_history(previous_messages)

            # Generate AI response
            # If only attachment (no audio), create a contextual prompt about the attachment
            if not transcribed_text and attachment_file:
                if attachment_type == 'pdf':
                    user_input = f"I've uploaded a PDF document: {attachment_name}. Can you help me with it?"
                elif attachment_type == 'image':
                    user_input = f"I've uploaded an image: {attachment_name}."
                elif attachment_type == 'document':
                    user_input = f"I've uploaded a document: {attachment_name}. Can you help me with it?"
                else:
                    user_input = f"I've uploaded a file: {attachment_name}."
            else:
                user_input = transcribed_text

            response_text, error = chat_service.generate_response(
                conversation_history,
                user_input
            )

            if error:
                logger.error(f"Chat response error: {error}")
                response_text = "I'm sorry, I'm having trouble responding right now. Please try again."

            # Create bot message
            bot_message = ChatMessage.objects.create(
                conversation=conversation,
                message_type='bot',
                response_text=response_text
            )

            # Update conversation metadata
            conversation.total_messages += 2
            conversation.save()

            # Return both messages
            return Response({
                'user_message': ChatMessageSerializer(user_message, context={'request': request}).data,
                'bot_message': ChatMessageSerializer(bot_message, context={'request': request}).data,
                'conversation_id': str(conversation.id)
            }, status=status.HTTP_201_CREATED)

        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending chat message: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your message'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def save_audio_file(self, audio_file, conversation_id):
        """Save audio file to media directory"""
        import uuid
        os.makedirs(settings.VOICE_FILES_DIR, exist_ok=True)
        file_extension = audio_file.name.split('.')[-1]
        filename = f"chat_{conversation_id}_{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(settings.VOICE_FILES_DIR, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in audio_file.chunks():
                destination.write(chunk)
        return file_path

    def save_attachment_file(self, attachment_file, conversation_id):
        """Save attachment file (PDF, image, document) to media directory"""
        import uuid

        # Create attachments directory
        attachments_dir = os.path.join(settings.MEDIA_ROOT, 'attachments')
        os.makedirs(attachments_dir, exist_ok=True)

        # Get file extension and determine type
        file_extension = attachment_file.name.split('.')[-1].lower()
        filename = f"attachment_{conversation_id}_{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(attachments_dir, filename)

        # Determine attachment type
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp']
        document_extensions = ['doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx']

        if file_extension == 'pdf':
            attachment_type = 'pdf'
        elif file_extension in image_extensions:
            attachment_type = 'image'
        elif file_extension in document_extensions:
            attachment_type = 'document'
        else:
            attachment_type = 'other'

        # Save file
        with open(file_path, 'wb+') as destination:
            for chunk in attachment_file.chunks():
                destination.write(chunk)

        return file_path, attachment_type

    def generate_title(self, text):
        """Generate a short title from the first message"""
        # Take first 50 characters or up to first sentence
        title = text[:50]
        if len(text) > 50:
            # Try to break at word boundary
            last_space = title.rfind(' ')
            if last_space > 20:
                title = title[:last_space]
            title += "..."
        return title


class GenerateSummaryView(APIView):
    """Generate a summary of a conversation"""

    def post(self, request):
        try:
            conversation_id = request.data.get('conversation_id')
            summary_type = request.data.get('summary_type', 'all')  # 'first' or 'all'

            if not conversation_id:
                return Response(
                    {'error': 'conversation_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get conversation and messages
            conversation = ChatConversation.objects.get(id=conversation_id)
            messages = conversation.messages.all().order_by('created_at')

            if not messages:
                return Response(
                    {'error': 'No messages to summarize'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate summary
            summary_service = SummaryService()
            summary, error = summary_service.generate_conversation_summary(messages, summary_type)

            if error:
                logger.error(f"Summary generation error: {error}")
                return Response(
                    {'error': 'Failed to generate summary'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Update conversation with summary
            conversation.conversation_summary = summary
            conversation.summary_generated_at = timezone.now()
            conversation.save()

            return Response({
                'summary': summary,
                'conversation_id': str(conversation.id),
                'generated_at': conversation.summary_generated_at
            }, status=status.HTTP_200_OK)

        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return Response(
                {'error': 'An error occurred while generating summary'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AskContextQuestionView(APIView):
    """Ask a question about a specific message in context"""

    def post(self, request):
        try:
            conversation_id = request.data.get('conversation_id')
            message_id = request.data.get('message_id')
            question = request.data.get('question')

            if not all([conversation_id, message_id, question]):
                return Response(
                    {'error': 'conversation_id, message_id, and question are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get conversation and messages
            conversation = ChatConversation.objects.get(id=conversation_id)
            message = ChatMessage.objects.get(id=message_id, conversation=conversation)
            conversation_history = conversation.messages.all().order_by('created_at')

            # Generate answer using context
            summary_service = SummaryService()
            answer, error = summary_service.answer_context_question(
                question, message, conversation_history
            )

            if error:
                logger.error(f"Context question error: {error}")
                return Response(
                    {'error': 'Failed to generate answer'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Store the question and answer
            context_question = ContextQuestion.objects.create(
                conversation=conversation,
                message=message,
                question=question,
                answer=answer,
                context_summary=conversation.conversation_summary
            )

            return Response({
                'question': question,
                'answer': answer,
                'message_id': str(message_id),
                'conversation_id': str(conversation_id),
                'question_id': str(context_question.id)
            }, status=status.HTTP_201_CREATED)

        except ChatConversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error answering context question: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your question'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetContextQuestionsView(APIView):
    """Get all context questions for a message or conversation"""

    def get(self, request):
        try:
            conversation_id = request.query_params.get('conversation_id')
            message_id = request.query_params.get('message_id')

            if not conversation_id:
                return Response(
                    {'error': 'conversation_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Filter by conversation
            questions = ContextQuestion.objects.filter(conversation_id=conversation_id)

            # Optionally filter by specific message
            if message_id:
                questions = questions.filter(message_id=message_id)

            questions = questions.order_by('-created_at')

            # Serialize the data
            questions_data = [{
                'id': str(q.id),
                'question': q.question,
                'answer': q.answer,
                'message_id': str(q.message.id),
                'created_at': q.created_at
            } for q in questions]

            return Response({
                'questions': questions_data,
                'count': len(questions_data)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving context questions: {str(e)}")
            return Response(
                {'error': 'An error occurred while retrieving questions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )