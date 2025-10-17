from django.contrib import admin
from .models import VoiceRequest, PhoneVerification, ChatConversation, ChatMessage


@admin.register(VoiceRequest)
class VoiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'intent', 'intent_confidence', 'file_format', 'file_size_mb', 'created_at']
    list_filter = ['status', 'intent', 'file_format', 'created_at']
    search_fields = ['id', 'transcribed_text', 'intent', 'intent_summary', 'user_ip']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at', 'user_ip', 'user_agent']
    
    fieldsets = (
        ('Basic Information', {'fields': ('id', 'status', 'error_message')}),
        ('File Information', {'fields': ('audio_file', 'file_size', 'file_format')}),
        ('Transcription', {'fields': ('transcribed_text',)}),
        ('Intent Classification', {'fields': ('intent', 'intent_confidence', 'intent_summary')}),
        ('Metadata', {'fields': ('user_ip', 'user_agent', 'created_at', 'updated_at', 'processed_at')}),
    )
    
    def file_size_mb(self, obj):
        return f"{obj.file_size / (1024*1024):.2f} MB"
    
    file_size_mb.short_description = 'File Size'
    
    def has_add_permission(self, request):
        return False


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone_number', 'is_verified', 'otp_code', 'verification_attempts', 'created_at', 'expires_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['phone_number', 'otp_code']
    readonly_fields = ['id', 'created_at', 'verified_at']

    fieldsets = (
        ('Phone Information', {'fields': ('id', 'phone_number')}),
        ('OTP Details', {'fields': ('otp_code', 'is_verified', 'verification_attempts')}),
        ('Timestamps', {'fields': ('created_at', 'verified_at', 'expires_at')}),
    )


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone_number', 'total_messages', 'last_activity', 'created_at']
    search_fields = ['phone_number']
    readonly_fields = ['id', 'created_at', 'last_activity']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'message_type', 'created_at', 'preview']
    list_filter = ['message_type', 'created_at']
    search_fields = ['transcribed_text', 'response_text']
    readonly_fields = ['id', 'created_at']

    def preview(self, obj):
        if obj.message_type == 'user':
            return (obj.transcribed_text[:50] + '...') if obj.transcribed_text and len(obj.transcribed_text) > 50 else obj.transcribed_text
        else:
            return (obj.response_text[:50] + '...') if obj.response_text and len(obj.response_text) > 50 else obj.response_text

    preview.short_description = 'Message Preview'