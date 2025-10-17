"""
Updated Serializers with entity extraction fields
File: voice_api/serializers.py
"""

from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from .models import VoiceRequest, PhoneVerification, ChatConversation, ChatMessage


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


class PhoneVerificationSerializer(serializers.ModelSerializer):
    """Serializer for PhoneVerification model"""

    class Meta:
        model = PhoneVerification
        fields = ['id', 'phone_number', 'is_verified', 'created_at', 'expires_at']
        read_only_fields = ['id', 'is_verified', 'created_at', 'expires_at']


class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP via email"""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate email format"""
        return value.strip().lower()


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP"""
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatMessage model"""

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'message_type', 'audio_file', 'transcribed_text',
            'response_text', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for ChatConversation with messages"""
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatConversation
        fields = ['id', 'phone_number', 'title', 'total_messages', 'last_activity', 'created_at', 'messages']
        read_only_fields = ['id', 'total_messages', 'last_activity', 'created_at']


class SendChatMessageSerializer(serializers.Serializer):
    """Serializer for sending chat messages with audio"""
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