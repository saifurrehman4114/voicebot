from django.contrib import admin
from .models import VoiceRequest, PhoneVerification, ChatConversation, ChatMessage, ContextQuestion, CalendarAppointment, AppointmentRecording


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
    list_display = ['id', 'conversation', 'message_type', 'intent', 'created_at', 'preview']
    list_filter = ['message_type', 'created_at']
    search_fields = ['transcribed_text', 'response_text', 'intent', 'keywords', 'topics']
    readonly_fields = ['id', 'intent', 'keywords', 'entities', 'domain_terms', 'action_items', 'topics', 'created_at']

    fieldsets = (
        ('Basic Information', {'fields': ('id', 'conversation', 'message_type', 'created_at')}),
        ('Content', {'fields': ('audio_file', 'transcribed_text', 'response_text')}),
        ('Attachments', {
            'fields': ('attachment_file', 'attachment_type', 'attachment_name', 'attachment_size'),
            'classes': ('collapse',)
        }),
        ('Entity Extraction', {
            'fields': ('intent', 'keywords', 'entities', 'domain_terms', 'action_items', 'topics'),
            'classes': ('collapse',)
        }),
    )

    def preview(self, obj):
        if obj.message_type == 'user':
            return (obj.transcribed_text[:50] + '...') if obj.transcribed_text and len(obj.transcribed_text) > 50 else obj.transcribed_text
        else:
            return (obj.response_text[:50] + '...') if obj.response_text and len(obj.response_text) > 50 else obj.response_text

    preview.short_description = 'Message Preview'


@admin.register(ContextQuestion)
class ContextQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'message', 'created_at', 'question_preview']
    list_filter = ['created_at']
    search_fields = ['question', 'answer']
    readonly_fields = ['id', 'created_at']

    def question_preview(self, obj):
        return (obj.question[:50] + '...') if len(obj.question) > 50 else obj.question

    question_preview.short_description = 'Question'


@admin.register(CalendarAppointment)
class CalendarAppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user_email', 'start_time', 'end_time', 'status', 'auto_record', 'reminder_sent']
    list_filter = ['status', 'auto_record', 'reminder_sent', 'start_time']
    search_fields = ['title', 'user_email', 'description', 'location']
    readonly_fields = ['id', 'duration_minutes', 'reminder_sent_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {'fields': ('id', 'user_email', 'title', 'description', 'color')}),
        ('Schedule', {'fields': ('start_time', 'end_time', 'duration_minutes')}),
        ('Recording Settings', {'fields': ('auto_record', 'reminder_minutes_before', 'reminder_sent', 'reminder_sent_at')}),
        ('Status', {'fields': ('status',)}),
        ('Meeting Details', {'fields': ('location', 'attendees')}),
        ('Notes', {'fields': ('notes',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        return True


@admin.register(AppointmentRecording)
class AppointmentRecordingAdmin(admin.ModelAdmin):
    list_display = ['id', 'appointment', 'recording_status', 'duration_minutes', 'intent', 'recording_started_at', 'processed_at']
    list_filter = ['recording_status', 'recording_started_at', 'processed_at']
    search_fields = ['appointment__title', 'transcribed_text', 'summary', 'intent']
    readonly_fields = ['id', 'transcribed_text', 'summary', 'intent', 'intent_confidence',
                      'keywords', 'entities', 'domain_terms', 'action_items', 'topics',
                      'processed_at', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {'fields': ('id', 'appointment', 'recording_status', 'error_message')}),
        ('Recording Details', {'fields': ('audio_file', 'file_size', 'file_format')}),
        ('Transcription', {'fields': ('transcribed_text',)}),
        ('AI Analysis', {
            'fields': ('summary', 'intent', 'intent_confidence')
        }),
        ('Entity Extraction', {
            'fields': ('keywords', 'entities', 'domain_terms', 'action_items', 'topics')
        }),
        ('Recording Metadata', {'fields': ('recording_started_at', 'recording_ended_at', 'duration_seconds')}),
        ('Processing', {'fields': ('processed_at', 'created_at', 'updated_at')}),
    )

    def duration_minutes(self, obj):
        if obj.duration_seconds:
            return f"{obj.duration_seconds / 60:.1f} min"
        return "N/A"

    duration_minutes.short_description = 'Duration'

    def has_add_permission(self, request):
        return False