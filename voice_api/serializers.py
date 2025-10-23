"""
Updated Serializers with entity extraction fields
File: voice_api/serializers.py
"""

from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from .models import VoiceRequest, PhoneVerification, ChatConversation, ChatMessage, CalendarAppointment, AppointmentRecording


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
    """Serializer for ChatMessage model with entity extraction and file attachments"""
    audio_file = serializers.SerializerMethodField()
    attachment_file = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'message_type', 'audio_file', 'transcribed_text',
            'attachment_file', 'attachment_type', 'attachment_name', 'attachment_size',
            'response_text', 'intent', 'keywords', 'entities',
            'domain_terms', 'action_items', 'topics', 'created_at'
        ]
        read_only_fields = [
            'id', 'intent', 'keywords', 'entities',
            'domain_terms', 'action_items', 'topics', 'created_at'
        ]

    def get_audio_file(self, obj):
        """Convert file path to media URL"""
        if obj.audio_file:
            # Extract just the filename from the full path
            import os
            filename = os.path.basename(obj.audio_file)
            # Return media URL
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/media/voice_recordings/{filename}')
            return f'/media/voice_recordings/{filename}'
        return None

    def get_attachment_file(self, obj):
        """Convert attachment file path to media URL"""
        if obj.attachment_file:
            import os
            filename = os.path.basename(obj.attachment_file)
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/media/attachments/{filename}')
            return f'/media/attachments/{filename}'
        return None


class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for ChatConversation with messages"""
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatConversation
        fields = ['id', 'phone_number', 'title', 'total_messages', 'last_activity', 'created_at', 'messages']
        read_only_fields = ['id', 'total_messages', 'last_activity', 'created_at']


class SendChatMessageSerializer(serializers.Serializer):
    """Serializer for sending chat messages with audio and optional file attachments"""
    audio_file = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['wav', 'mp3', 'ogg', 'webm', 'm4a', 'flac']
            )
        ]
    )

    attachment_file = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx',
                    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
                    'zip', 'rar', '7z', 'tar', 'gz'
                ]
            )
        ]
    )

    def validate_audio_file(self, value):
        """Validate audio file size"""
        if value:
            from django.conf import settings
            if value.size > settings.MAX_UPLOAD_SIZE:
                raise serializers.ValidationError(
                    f"Audio file size cannot exceed {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
                )
        return value

    def validate_attachment_file(self, value):
        """Validate attachment file size"""
        if value:
            from django.conf import settings
            # Allow larger size for attachments (50MB)
            max_attachment_size = 50 * 1024 * 1024  # 50MB
            if value.size > max_attachment_size:
                raise serializers.ValidationError(
                    f"Attachment file size cannot exceed {max_attachment_size / (1024*1024)}MB"
                )
        return value

    def validate(self, data):
        """Ensure at least audio or attachment is provided"""
        if not data.get('audio_file') and not data.get('attachment_file'):
            raise serializers.ValidationError(
                "Either audio_file or attachment_file must be provided"
            )
        return data


class AppointmentRecordingSerializer(serializers.ModelSerializer):
    """Serializer for AppointmentRecording model"""

    class Meta:
        model = AppointmentRecording
        fields = [
            'id', 'appointment', 'audio_file', 'file_size', 'file_format',
            'transcribed_text', 'summary', 'intent', 'intent_confidence',
            'keywords', 'entities', 'domain_terms', 'action_items', 'topics',
            'recording_status', 'recording_started_at', 'recording_ended_at',
            'duration_seconds', 'processed_at', 'error_message', 'created_at'
        ]
        read_only_fields = [
            'id', 'transcribed_text', 'summary', 'intent', 'intent_confidence',
            'keywords', 'entities', 'domain_terms', 'action_items', 'topics',
            'recording_status', 'processed_at', 'error_message', 'created_at'
        ]


class CalendarAppointmentSerializer(serializers.ModelSerializer):
    """Serializer for CalendarAppointment model"""
    recordings = AppointmentRecordingSerializer(many=True, read_only=True)

    class Meta:
        model = CalendarAppointment
        fields = [
            'id', 'user_email', 'title', 'description',
            'start_time', 'end_time', 'duration_minutes',
            'auto_record', 'reminder_minutes_before', 'reminder_sent', 'reminder_sent_at',
            'status', 'color', 'location', 'attendees', 'notes',
            'created_at', 'updated_at', 'recordings'
        ]
        read_only_fields = ['id', 'duration_minutes', 'reminder_sent', 'reminder_sent_at', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate appointment times"""
        if 'start_time' in data and 'end_time' in data:
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError("End time must be after start time")
        return data


class CreateAppointmentSerializer(serializers.Serializer):
    """Serializer for creating an appointment"""
    title = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField(required=True)
    end_time = serializers.DateTimeField(required=True)
    auto_record = serializers.BooleanField(default=True)
    reminder_minutes_before = serializers.IntegerField(default=5, min_value=0)
    location = serializers.CharField(max_length=500, required=False, allow_blank=True)
    attendees = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        allow_empty=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(max_length=7, default='#8B5CF6')

    def validate(self, data):
        """Validate appointment data"""
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data


class UploadRecordingSerializer(serializers.Serializer):
    """Serializer for uploading appointment recording"""
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