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

from .models import VoiceRequest
from .serializers import VoiceRequestSerializer, VoiceUploadSerializer
from .services.speech_to_text_service import SpeechToTextService
from .services.intent_classifier_service import IntentClassifierService
from .services.entity_extraction_service import EntityExtractionService  # NEW

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