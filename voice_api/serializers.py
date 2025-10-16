"""
Updated Serializers with entity extraction fields
File: voice_api/serializers.py
"""

from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from .models import VoiceRequest


class VoiceRequestSerializer(serializers.ModelSerializer):
    """Serializer for VoiceRequest model with entity extraction"""
    
    class Meta:
        model = VoiceRequest
        fields = [
            'id', 'audio_file', 'file_size', 'file_format',
            'transcribed_text', 'intent', 'intent_confidence', 'intent_summary',
            # NEW: Entity extraction fields
            'keywords', 'entities', 'domain_terms', 'action_items', 'topics',
            'status', 'error_message', 'created_at', 'updated_at',
            'processed_at'
        ]
        read_only_fields = [
            'id', 'transcribed_text', 'intent', 'intent_confidence', 'intent_summary',
            'keywords', 'entities', 'domain_terms', 'action_items', 'topics',
            'status', 'error_message', 'created_at', 'updated_at',
            'processed_at'
        ]


class VoiceUploadSerializer(serializers.Serializer):
    """Serializer for voice file upload"""
    
    audio_file = serializers.FileField(
        required=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['wav', 'mp3', 'ogg', 'webm', 'm4a', 'flac']
            )
        ]
    )
    
    def validate_audio_file(self, value):
        """Validate file size"""
        from django.conf import settings
        
        if value.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f"File size cannot exceed {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
            )
        return value