"""
Updated Database models for voice_api with entity extraction
File: voice_api/models.py
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class VoiceRequest(models.Model):
    """Model to store voice recording requests with dynamic AI-generated intent"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audio_file = models.CharField(max_length=500, help_text="Path to audio file")
    file_size = models.IntegerField(help_text="File size in bytes")
    file_format = models.CharField(max_length=10)
    
    # Transcription
    transcribed_text = models.TextField(blank=True, null=True)
    
    # Intent classification
    intent = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="AI-generated intent category"
    )
    intent_confidence = models.FloatField(blank=True, null=True)
    intent_summary = models.TextField(blank=True, null=True, help_text="Brief summary of request")
    
    # Entity extraction - NEW FIELDS
    keywords = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="Important keywords extracted from transcription"
    )
    entities = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Named entities (people, places, organizations)"
    )
    domain_terms = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Domain-specific technical terms"
    )
    action_items = ArrayField(
        models.TextField(),
        blank=True,
        default=list,
        help_text="Action items or tasks mentioned"
    )
    topics = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Main topics/themes discussed"
    )
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    # Additional metadata
    user_ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'voice_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['intent']),
            models.Index(fields=['keywords']),  # Index for searching by keywords
        ]
    
    def __str__(self):
        return f"VoiceRequest {self.id} - {self.status}"