from django.contrib import admin
from .models import VoiceRequest


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