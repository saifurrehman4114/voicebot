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


class PhoneVerification(models.Model):
    """Model to store OTP verification for email-based authentication"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=255, help_text="Email address for verification", db_column='phone_number')  # Keep column name for backward compatibility
    otp_code = models.CharField(max_length=6, help_text="6-digit OTP code")
    is_verified = models.BooleanField(default=False)
    verification_attempts = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(help_text="OTP expiration time")

    class Meta:
        db_table = 'phone_verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'is_verified']),
            models.Index(fields=['otp_code']),
        ]

    def __str__(self):
        return f"Verification for {self.phone_number} - {'Verified' if self.is_verified else 'Pending'}"


class ChatConversation(models.Model):
    """Model to track conversation threads for each user"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=255, help_text="User's email address", db_column='phone_number')  # Removed unique constraint for multiple conversations

    # Conversation metadata
    title = models.CharField(max_length=255, default="New Chat", help_text="Auto-generated conversation title")
    total_messages = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Summary and context
    conversation_summary = models.TextField(blank=True, null=True, help_text="AI-generated summary of the conversation")
    summary_generated_at = models.DateTimeField(blank=True, null=True, help_text="When the summary was last updated")

    class Meta:
        db_table = 'chat_conversations'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['phone_number', '-last_activity']),
        ]

    def __str__(self):
        return f"{self.title} - {self.phone_number}"


class ChatMessage(models.Model):
    """Model to store individual chat messages with audio and responses"""

    MESSAGE_TYPE_CHOICES = [
        ('user', 'User'),
        ('bot', 'Bot'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    # Message details
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)

    # For user messages (audio)
    audio_file = models.CharField(max_length=500, blank=True, null=True, help_text="Path to audio file")
    transcribed_text = models.TextField(blank=True, null=True)

    # File attachments (PDFs, images, documents)
    attachment_file = models.CharField(max_length=500, blank=True, null=True, help_text="Path to attachment file")
    attachment_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('image', 'Image'),
            ('pdf', 'PDF Document'),
            ('document', 'Document'),
            ('other', 'Other'),
        ],
        help_text="Type of attachment"
    )
    attachment_name = models.CharField(max_length=255, blank=True, null=True, help_text="Original filename")
    attachment_size = models.IntegerField(blank=True, null=True, help_text="File size in bytes")

    # For bot messages (text response)
    response_text = models.TextField(blank=True, null=True)

    # Entity extraction for user messages
    intent = models.CharField(max_length=200, blank=True, null=True, help_text="Message intent")
    keywords = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="Important keywords from the message"
    )
    entities = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Named entities mentioned"
    )
    domain_terms = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Technical or domain-specific terms"
    )
    action_items = ArrayField(
        models.TextField(),
        blank=True,
        default=list,
        help_text="Action items and tasks identified"
    )
    topics = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Topics discussed in the message"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['message_type']),
        ]

    def __str__(self):
        return f"{self.message_type} message in {self.conversation.phone_number} at {self.created_at}"


class ContextQuestion(models.Model):
    """Model to store context-based questions asked about messages"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='context_questions'
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='context_questions',
        help_text="The message this question is about"
    )

    # Question and response
    question = models.TextField(help_text="User's question about the context")
    answer = models.TextField(help_text="AI-generated answer")

    # Context stored at time of question
    context_summary = models.TextField(blank=True, null=True, help_text="Summary of context when question was asked")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'context_questions'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['message']),
        ]

    def __str__(self):
        return f"Question about message {self.message.id} at {self.created_at}"


class CalendarAppointment(models.Model):
    """Model to store calendar appointments with recording capabilities"""

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('reminder_sent', 'Reminder Sent'),
        ('recording', 'Recording in Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_email = models.CharField(max_length=255, help_text="User's email address")

    # Appointment details
    title = models.CharField(max_length=255, help_text="Appointment title")
    description = models.TextField(blank=True, null=True, help_text="Appointment description")

    # Scheduling
    start_time = models.DateTimeField(help_text="Appointment start date and time")
    end_time = models.DateTimeField(help_text="Appointment end date and time")
    duration_minutes = models.IntegerField(help_text="Duration in minutes")

    # Recording settings
    auto_record = models.BooleanField(default=True, help_text="Automatically start recording at appointment time")
    reminder_minutes_before = models.IntegerField(default=5, help_text="Send reminder N minutes before appointment")
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(blank=True, null=True)

    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    color = models.CharField(max_length=7, default='#8B5CF6', help_text="Hex color code for calendar display")

    # Location/meeting details
    location = models.CharField(max_length=500, blank=True, null=True, help_text="Physical or virtual location")

    # Attendees
    attendees = ArrayField(
        models.EmailField(),
        blank=True,
        default=list,
        help_text="Email addresses of attendees"
    )

    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")

    # Conversation link
    conversation_id = models.UUIDField(blank=True, null=True, help_text="Linked chat conversation ID")
    conversation_link_sent = models.BooleanField(default=False, help_text="Whether conversation link email was sent")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'calendar_appointments'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['user_email', 'start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['start_time', 'end_time']),
        ]

    def __str__(self):
        return f"{self.title} - {self.start_time}"


class AppointmentRecording(models.Model):
    """Model to store recordings and summaries for appointments"""

    RECORDING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('recording', 'Recording'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        CalendarAppointment,
        on_delete=models.CASCADE,
        related_name='recordings'
    )

    # Recording details
    audio_file = models.CharField(max_length=500, blank=True, null=True, help_text="Path to audio file")
    file_size = models.IntegerField(blank=True, null=True, help_text="File size in bytes")
    file_format = models.CharField(max_length=10, blank=True, null=True)

    # Transcription
    transcribed_text = models.TextField(blank=True, null=True)

    # AI-powered analysis
    summary = models.TextField(blank=True, null=True, help_text="AI-generated summary of the recording")
    intent = models.CharField(max_length=200, blank=True, null=True, help_text="Main intent/purpose of the meeting")
    intent_confidence = models.FloatField(blank=True, null=True)

    # Entity extraction
    keywords = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        help_text="Important keywords from the meeting"
    )
    entities = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Named entities mentioned"
    )
    domain_terms = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Technical or domain-specific terms"
    )
    action_items = ArrayField(
        models.TextField(),
        blank=True,
        default=list,
        help_text="Action items and tasks identified"
    )
    topics = ArrayField(
        models.CharField(max_length=200),
        blank=True,
        default=list,
        help_text="Topics discussed in the meeting"
    )

    # Recording metadata
    recording_status = models.CharField(max_length=20, choices=RECORDING_STATUS_CHOICES, default='pending')
    recording_started_at = models.DateTimeField(blank=True, null=True)
    recording_ended_at = models.DateTimeField(blank=True, null=True)
    duration_seconds = models.IntegerField(blank=True, null=True)

    # Processing metadata
    processed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointment_recordings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['appointment', '-created_at']),
            models.Index(fields=['recording_status']),
        ]

    def __str__(self):
        return f"Recording for {self.appointment.title} - {self.recording_status}"