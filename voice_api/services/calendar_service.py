"""
Calendar Appointment Service for scheduling and reminder management
File: voice_api/services/calendar_service.py
"""

from datetime import datetime, timedelta
from django.utils import timezone
from voice_api.models import CalendarAppointment, AppointmentRecording, ChatConversation
from voice_api.services.otp_service import OTPService
import logging
import uuid

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for managing calendar appointments and reminders"""

    @staticmethod
    def create_appointment(user_email, title, description, start_time, end_time,
                          auto_record=True, reminder_minutes_before=5,
                          location=None, attendees=None,
                          notes=None, color='#8B5CF6', base_url=None):
        """
        Create a new calendar appointment

        Args:
            user_email: User's email address
            title: Appointment title
            description: Appointment description
            start_time: Start datetime
            end_time: End datetime
            auto_record: Whether to auto-record
            reminder_minutes_before: Minutes before appointment to send reminder
            location: Physical or virtual location
            attendees: List of attendee email addresses
            notes: Additional notes
            color: Hex color code for calendar display

        Returns:
            CalendarAppointment instance
        """
        try:
            # Calculate duration
            duration = end_time - start_time
            duration_minutes = int(duration.total_seconds() / 60)

            appointment = CalendarAppointment.objects.create(
                user_email=user_email,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                auto_record=auto_record,
                reminder_minutes_before=reminder_minutes_before,
                location=location,
                attendees=attendees or [],
                notes=notes,
                color=color,
                base_url=base_url,
                status='scheduled'
            )

            logger.info(f"Created appointment: {appointment.id} for {user_email}")
            return appointment

        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            raise

    @staticmethod
    def update_appointment(appointment_id, **kwargs):
        """
        Update an existing appointment

        Args:
            appointment_id: UUID of appointment
            **kwargs: Fields to update

        Returns:
            Updated CalendarAppointment instance
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Update duration if times change
            if 'start_time' in kwargs or 'end_time' in kwargs:
                start = kwargs.get('start_time', appointment.start_time)
                end = kwargs.get('end_time', appointment.end_time)
                duration = end - start
                kwargs['duration_minutes'] = int(duration.total_seconds() / 60)

            for key, value in kwargs.items():
                setattr(appointment, key, value)

            appointment.save()
            logger.info(f"Updated appointment: {appointment_id}")
            return appointment

        except CalendarAppointment.DoesNotExist:
            logger.error(f"Appointment not found: {appointment_id}")
            raise
        except Exception as e:
            logger.error(f"Error updating appointment: {str(e)}")
            raise

    @staticmethod
    def delete_appointment(appointment_id):
        """
        Delete an appointment

        Args:
            appointment_id: UUID of appointment
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)
            appointment.delete()
            logger.info(f"Deleted appointment: {appointment_id}")

        except CalendarAppointment.DoesNotExist:
            logger.error(f"Appointment not found: {appointment_id}")
            raise
        except Exception as e:
            logger.error(f"Error deleting appointment: {str(e)}")
            raise

    @staticmethod
    def cancel_appointment(appointment_id):
        """
        Cancel an appointment (soft delete)

        Args:
            appointment_id: UUID of appointment

        Returns:
            Updated appointment
        """
        return CalendarService.update_appointment(
            appointment_id,
            status='cancelled'
        )

    @staticmethod
    def get_appointments(user_email, start_date=None, end_date=None, status=None):
        """
        Get appointments for a user within a date range

        Args:
            user_email: User's email address
            start_date: Start of date range (optional)
            end_date: End of date range (optional)
            status: Filter by status (optional)

        Returns:
            QuerySet of appointments
        """
        queryset = CalendarAppointment.objects.filter(user_email=user_email)

        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__lte=end_date)
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('start_time')

    @staticmethod
    def get_upcoming_appointments(user_email, hours=24):
        """
        Get upcoming appointments within the next N hours

        Args:
            user_email: User's email address
            hours: Number of hours to look ahead

        Returns:
            QuerySet of appointments
        """
        now = timezone.now()
        end_time = now + timedelta(hours=hours)

        return CalendarAppointment.objects.filter(
            user_email=user_email,
            start_time__gte=now,
            start_time__lte=end_time,
            status='scheduled'
        ).order_by('start_time')

    @staticmethod
    def get_appointments_needing_reminders():
        """
        Get appointments that need reminder notifications sent
        Only returns appointments that haven't been reminded yet

        Returns:
            QuerySet of appointments
        """
        now = timezone.now()

        # IMPORTANT: Only get appointments that haven't been reminded yet
        appointments = CalendarAppointment.objects.filter(
            status='scheduled',
            reminder_sent=False,  # Never sent reminder before
            auto_record=True
        )

        # Filter for appointments whose reminder time has passed
        appointments_to_remind = []
        for apt in appointments:
            reminder_time = apt.start_time - timedelta(minutes=apt.reminder_minutes_before)
            if now >= reminder_time and now < apt.start_time:  # Only before appointment starts
                appointments_to_remind.append(apt.id)

        return CalendarAppointment.objects.filter(id__in=appointments_to_remind)

    @staticmethod
    def send_reminder(appointment_id):
        """
        Send a reminder notification for an appointment
        Creates conversation and includes link in reminder email

        Args:
            appointment_id: UUID of appointment

        Returns:
            Boolean indicating success
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Check if reminder already sent to prevent duplicates
            if appointment.reminder_sent:
                logger.warning(f"Reminder already sent for appointment: {appointment_id}")
                return False

            # Get or create ONE conversation for this appointment
            conversation = None
            try:
                logger.info(f"   → Getting/creating conversation for appointment")
                conversation = CalendarService.create_appointment_conversation(appointment_id)
                logger.info(f"   → Conversation ID: {conversation.id}")
            except Exception as conv_error:
                logger.error(f"   → Failed to create conversation: {str(conv_error)}")
                import traceback
                logger.error(f"   → Traceback: {traceback.format_exc()}")
                # Continue anyway, will create later if needed

            # Send email reminder
            otp_service = OTPService()

            # Calculate time until appointment
            now = timezone.now()
            time_diff = appointment.start_time - now
            minutes_until = int(time_diff.total_seconds() / 60)

            subject = f"⏰ Reminder: {appointment.title} starting in {minutes_until} minutes"

            # Build conversation URL if conversation exists
            from django.conf import settings
            conversation_url = ""
            if conversation:
                # Get base URL - checks both production and localhost dynamically
                base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
                # If appointment has a stored base_url from when it was created, use that
                if hasattr(appointment, 'base_url') and appointment.base_url:
                    base_url = appointment.base_url
                conversation_url = f"{base_url}/chat/?conversation={conversation.id}&appointment_id={appointment.id}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-size: 32px;
                        font-weight: bold;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    }}
                    .appointment-card {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        border-radius: 12px;
                        margin: 20px 0;
                    }}
                    .appointment-title {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 15px;
                    }}
                    .appointment-details {{
                        font-size: 16px;
                        line-height: 1.8;
                    }}
                    .detail-row {{
                        margin: 10px 0;
                        display: flex;
                        align-items: center;
                    }}
                    .detail-label {{
                        font-weight: 600;
                        margin-right: 10px;
                        min-width: 100px;
                    }}
                    .recording-notice {{
                        background: #FEF3C7;
                        border-left: 4px solid #F59E0B;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                        color: #92400E;
                    }}
                    .cta-button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        padding: 16px 40px;
                        border-radius: 12px;
                        font-size: 16px;
                        font-weight: 600;
                        margin: 24px 0;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        color: #666;
                        font-size: 14px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">📅 Voicebot AI Calendar</div>
                        <h2 style="color: #667eea; margin-top: 20px;">⏰ Appointment Reminder</h2>
                    </div>

                    <p style="text-align: center; font-size: 18px; color: #333; margin: 20px 0;">
                        <strong>Your appointment starts in {minutes_until} minutes!</strong>
                    </p>

                    <div class="appointment-card">
                        <div class="appointment-title">{appointment.title}</div>
                        <div class="appointment-details">
                            <div class="detail-row">
                                <span class="detail-label">🕐 Start Time:</span>
                                <span>{appointment.start_time.strftime('%B %d, %Y at %I:%M %p')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">⏱️ Duration:</span>
                                <span>{appointment.duration_minutes} minutes</span>
                            </div>
                            {f'<div class="detail-row"><span class="detail-label">📍 Location:</span><span>{appointment.location}</span></div>' if appointment.location else ''}
                        </div>
                    </div>

                    {f'<div class="recording-notice"><strong>🎙️ Recording Notice:</strong> This meeting will be automatically recorded when it starts. You can access your conversation and start recording now using the button below.</div>' if appointment.auto_record else ''}

                    {f'<p style="color: #666; line-height: 1.6; margin: 20px 0;">{appointment.description}</p>' if appointment.description else ''}

                    {f'''<div style="text-align: center; margin: 30px 0;">
                        <a href="{conversation_url}" class="cta-button">
                            💬 Open Chat & Start Recording
                        </a>
                        <p style="color: #999; font-size: 14px; margin-top: 10px;">
                            Click to access your dedicated conversation for this appointment
                        </p>
                    </div>''' if conversation_url else ''}

                    <div class="footer">
                        <p>This is an automated reminder from Voicebot AI Calendar</p>
                        <p>Powered by Voicebot AI 🤖</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send email via Brevo
            import requests
            import os

            brevo_api_key = os.getenv('BREVO_API_KEY')
            sender_email = os.getenv('BREVO_SENDER_EMAIL', 'noreply@voicebotai.com')

            if not brevo_api_key:
                logger.error("BREVO_API_KEY not configured")
                return False

            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json"
            }

            payload = {
                "sender": {"email": sender_email, "name": "Voicebot AI Calendar"},
                "to": [{"email": appointment.user_email}],
                "subject": subject,
                "htmlContent": html_content
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 201:
                # Update appointment
                appointment.reminder_sent = True
                appointment.reminder_sent_at = timezone.now()
                appointment.status = 'reminder_sent'
                appointment.save()

                logger.info(f"Sent reminder for appointment: {appointment_id}")
                return True
            else:
                logger.error(f"Failed to send reminder: {response.text}")
                return False

        except CalendarAppointment.DoesNotExist:
            logger.error(f"Appointment not found: {appointment_id}")
            return False
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
            return False

    @staticmethod
    def get_appointments_to_start_recording():
        """
        Get appointments that should start recording now

        Returns:
            QuerySet of appointments
        """
        now = timezone.now()

        return CalendarAppointment.objects.filter(
            status__in=['scheduled', 'reminder_sent'],
            auto_record=True,
            start_time__lte=now,
            end_time__gte=now
        )

    @staticmethod
    def get_appointments_to_stop_recording():
        """
        Get appointments that should stop recording now

        Returns:
            QuerySet of appointments
        """
        now = timezone.now()

        return CalendarAppointment.objects.filter(
            status='recording',
            end_time__lte=now
        )

    @staticmethod
    def start_recording_notification(appointment_id):
        """
        Send notification that recording is starting

        Args:
            appointment_id: UUID of appointment

        Returns:
            Boolean indicating success
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Send email notification
            otp_service = OTPService()

            subject = f"🎙️ Recording Started: {appointment.title}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .recording-badge {{
                        background: #EF4444;
                        color: white;
                        padding: 15px 30px;
                        border-radius: 50px;
                        font-size: 20px;
                        font-weight: bold;
                        display: inline-block;
                        animation: pulse 2s infinite;
                    }}
                    @keyframes pulse {{
                        0%, 100% {{ opacity: 1; }}
                        50% {{ opacity: 0.7; }}
                    }}
                    .content {{
                        text-align: center;
                        color: #333;
                        line-height: 1.8;
                    }}
                    .appointment-title {{
                        font-size: 24px;
                        font-weight: bold;
                        margin: 20px 0;
                        color: #667eea;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="recording-badge">🎙️ RECORDING IN PROGRESS</div>
                    </div>

                    <div class="content">
                        <div class="appointment-title">{appointment.title}</div>
                        <p>Recording has started for your appointment.</p>
                        <p>The audio will be automatically transcribed and summarized when the recording ends.</p>
                        <p><strong>Duration:</strong> {appointment.duration_minutes} minutes</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send email via Brevo
            import requests
            import os

            brevo_api_key = os.getenv('BREVO_API_KEY')
            sender_email = os.getenv('BREVO_SENDER_EMAIL', 'noreply@voicebotai.com')

            if not brevo_api_key:
                logger.error("BREVO_API_KEY not configured")
                return False

            url = "https://api.brevo.com/v3/smtp/email"
            headers = {
                "accept": "application/json",
                "api-key": brevo_api_key,
                "content-type": "application/json"
            }

            payload = {
                "sender": {"email": sender_email, "name": "Voicebot AI Calendar"},
                "to": [{"email": appointment.user_email}],
                "subject": subject,
                "htmlContent": html_content
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 201:
                logger.info(f"Sent recording notification for appointment: {appointment_id}")
                return True
            else:
                logger.error(f"Failed to send recording notification: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending recording notification: {str(e)}")
            return False

    @staticmethod
    def send_conversation_link_email(appointment_id, conversation_id, user_email):
        """
        Send email with chat conversation link when appointment recording starts

        Args:
            appointment_id: UUID of appointment
            conversation_id: UUID of the created conversation
            user_email: User's email address

        Returns:
            Boolean indicating success
        """
        try:
            from django.conf import settings
            import requests

            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Build conversation URL
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            conversation_url = f"{base_url}/chat/?conversation={conversation_id}&appointment_id={appointment_id}"

            subject = f"🎙️ Recording Started: {appointment.title}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-size: 32px;
                        font-weight: bold;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    }}
                    .icon {{
                        font-size: 64px;
                        margin: 20px 0;
                    }}
                    .title {{
                        font-size: 24px;
                        font-weight: 700;
                        color: #333;
                        margin: 20px 0;
                    }}
                    .appointment-card {{
                        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                        padding: 24px;
                        border-radius: 12px;
                        margin: 20px 0;
                        border-left: 4px solid #667eea;
                    }}
                    .appointment-title {{
                        font-size: 20px;
                        font-weight: bold;
                        color: #667eea;
                        margin-bottom: 12px;
                    }}
                    .detail-row {{
                        margin: 8px 0;
                        color: #666;
                        font-size: 15px;
                    }}
                    .detail-label {{
                        font-weight: 600;
                        color: #333;
                    }}
                    .cta-button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        padding: 16px 40px;
                        border-radius: 12px;
                        font-size: 16px;
                        font-weight: 600;
                        margin: 24px 0;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                        transition: all 0.3s;
                    }}
                    .cta-button:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
                    }}
                    .info-box {{
                        background: #EFF6FF;
                        border-left: 4px solid #3B82F6;
                        padding: 16px;
                        border-radius: 8px;
                        margin: 20px 0;
                        color: #1E40AF;
                        font-size: 14px;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        color: #666;
                        font-size: 14px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🤖 Voicebot AI</div>
                        <div class="icon">🎙️</div>
                        <div class="title">Your Appointment Recording Has Started</div>
                    </div>

                    <p style="font-size: 16px; line-height: 1.6; color: #666;">
                        The recording for your scheduled appointment has automatically started.
                        You can access the conversation and all recordings at any time.
                    </p>

                    <div class="appointment-card">
                        <div class="appointment-title">📅 {appointment.title}</div>
                        <div class="detail-row">
                            <span class="detail-label">Start Time:</span>
                            {appointment.start_time.strftime('%B %d, %Y at %I:%M %p')}
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Duration:</span>
                            {appointment.duration_minutes} minutes
                        </div>
                        {f'<div class="detail-row"><span class="detail-label">Location:</span> {appointment.location}</div>' if appointment.location else ''}
                    </div>

                    <div style="text-align: center;">
                        <a href="{conversation_url}" class="cta-button">
                            🎵 View Conversation & Recording
                        </a>
                    </div>

                    <div class="info-box">
                        <strong>💡 Tip:</strong> All your recordings are automatically transcribed and analyzed.
                        You can ask questions about the conversation, review summaries, and access insights anytime!
                    </div>

                    <div class="footer">
                        <p>This is an automated email from Voicebot AI</p>
                        <p>You're receiving this because you have an appointment with automatic recording enabled.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send email via Brevo
            api_key = settings.BREVO_API_KEY
            url = 'https://api.brevo.com/v3/smtp/email'

            headers = {
                'accept': 'application/json',
                'api-key': api_key,
                'content-type': 'application/json'
            }

            data = {
                'sender': {
                    'name': 'Voicebot AI',
                    'email': 'noreply@voicebotai.com'
                },
                'to': [
                    {
                        'email': user_email,
                        'name': user_email.split('@')[0]
                    }
                ],
                'subject': subject,
                'htmlContent': html_content
            }

            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 201:
                logger.info(f"Sent conversation link email for appointment: {appointment_id}")
                return True
            else:
                logger.error(f"Failed to send conversation link email: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending conversation link email: {str(e)}")
            return False

    @staticmethod
    def create_appointment_conversation(appointment_id):
        """
        Create ONE conversation per appointment
        If conversation already exists, return it
        Each appointment has its own unique conversation

        Args:
            appointment_id: UUID of appointment

        Returns:
            ChatConversation instance
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Check if conversation already exists for this appointment
            if appointment.conversation_id:
                try:
                    existing_conv = ChatConversation.objects.get(id=appointment.conversation_id)
                    logger.info(f"Using existing conversation {existing_conv.id} for appointment {appointment_id}")
                    return existing_conv
                except ChatConversation.DoesNotExist:
                    # Conversation was deleted, create new one
                    logger.warning(f"Conversation {appointment.conversation_id} not found, creating new one")

            # Create conversation title
            conversation_title = f"🎙️ {appointment.title} - {appointment.start_time.strftime('%b %d, %Y')}"

            # Create new conversation
            conversation = ChatConversation.objects.create(
                phone_number=appointment.user_email,
                title=conversation_title,
                total_messages=0
            )

            # Link conversation to appointment
            appointment.conversation_id = conversation.id
            appointment.save()

            logger.info(f"Created conversation {conversation.id} for appointment {appointment_id}")
            return conversation

        except CalendarAppointment.DoesNotExist:
            logger.error(f"Appointment not found: {appointment_id}")
            raise
        except Exception as e:
            logger.error(f"Error creating appointment conversation: {str(e)}")
            raise

    @staticmethod
    def send_recording_started_email(appointment_id, conversation_id):
        """
        Send email notification when recording starts with conversation link

        Args:
            appointment_id: UUID of appointment
            conversation_id: UUID of conversation

        Returns:
            Boolean indicating success
        """
        try:
            from django.conf import settings
            import requests

            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Build conversation URL
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            conversation_url = f"{base_url}/chat/?conversation={conversation_id}&appointment_id={appointment_id}"

            subject = f"🎙️ Recording Started: {appointment.title}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-size: 32px;
                        font-weight: bold;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    }}
                    .icon {{
                        font-size: 64px;
                        margin: 20px 0;
                    }}
                    .recording-badge {{
                        background: #EF4444;
                        color: white;
                        padding: 12px 24px;
                        border-radius: 50px;
                        font-size: 16px;
                        font-weight: bold;
                        display: inline-block;
                        animation: pulse 2s infinite;
                    }}
                    @keyframes pulse {{
                        0%, 100% {{ opacity: 1; }}
                        50% {{ opacity: 0.7; }}
                    }}
                    .title {{
                        font-size: 24px;
                        font-weight: 700;
                        color: #333;
                        margin: 20px 0;
                    }}
                    .appointment-card {{
                        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
                        padding: 24px;
                        border-radius: 12px;
                        margin: 20px 0;
                        border-left: 4px solid #667eea;
                    }}
                    .cta-button {{
                        display: inline-block;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        padding: 16px 40px;
                        border-radius: 12px;
                        font-size: 16px;
                        font-weight: 600;
                        margin: 24px 0;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                    }}
                    .info-box {{
                        background: #FEF3C7;
                        border-left: 4px solid #F59E0B;
                        padding: 16px;
                        border-radius: 8px;
                        margin: 20px 0;
                        color: #92400E;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">🤖 Voicebot AI</div>
                        <div class="icon">🎙️</div>
                        <div class="recording-badge">● REC</div>
                        <div class="title">Recording Started!</div>
                    </div>

                    <p style="font-size: 16px; line-height: 1.6; color: #666; text-align: center;">
                        Your appointment recording has automatically started.<br>
                        Access your conversation and recording below.
                    </p>

                    <div class="appointment-card">
                        <div style="font-size: 20px; font-weight: bold; color: #667eea; margin-bottom: 12px;">
                            📅 {appointment.title}
                        </div>
                        <div style="margin: 8px 0; color: #666;">
                            <strong>Start:</strong> {appointment.start_time.strftime('%B %d, %Y at %I:%M %p')}
                        </div>
                        <div style="margin: 8px 0; color: #666;">
                            <strong>Duration:</strong> {appointment.duration_minutes} minutes
                        </div>
                        {f'<div style="margin: 8px 0; color: #666;"><strong>Location:</strong> {appointment.location}</div>' if appointment.location else ''}
                    </div>

                    <div style="text-align: center;">
                        <a href="{conversation_url}" class="cta-button">
                            💬 Open Conversation & Recording
                        </a>
                    </div>

                    <div class="info-box">
                        <strong>📝 What happens next:</strong><br>
                        • Your conversation is being recorded<br>
                        • Audio will be automatically transcribed<br>
                        • AI will generate a summary with action items<br>
                        • You'll receive the summary when recording ends
                    </div>

                    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 14px;">
                        <p>This is an automated email from Voicebot AI</p>
                        <p>Powered by Voicebot AI 🤖</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send email via Brevo
            api_key = getattr(settings, 'BREVO_API_KEY', None)
            if not api_key:
                logger.error("BREVO_API_KEY not configured")
                return False

            url = 'https://api.brevo.com/v3/smtp/email'
            headers = {
                'accept': 'application/json',
                'api-key': api_key,
                'content-type': 'application/json'
            }

            data = {
                'sender': {
                    'name': 'Voicebot AI',
                    'email': getattr(settings, 'BREVO_SENDER_EMAIL', 'noreply@voicebotai.com')
                },
                'to': [{'email': appointment.user_email}],
                'subject': subject,
                'htmlContent': html_content
            }

            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 201:
                # Mark email as sent
                appointment.conversation_link_sent = True
                appointment.save()
                logger.info(f"Sent recording started email for appointment: {appointment_id}")
                return True
            else:
                logger.error(f"Failed to send recording started email: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending recording started email: {str(e)}")
            return False

    @staticmethod
    def send_completion_summary_email(appointment_id, recording):
        """
        Send email with recording summary and analysis

        Args:
            appointment_id: UUID of appointment
            recording: AppointmentRecording instance with summary

        Returns:
            Boolean indicating success
        """
        try:
            from django.conf import settings
            import requests

            appointment = CalendarAppointment.objects.get(id=appointment_id)

            subject = f"✅ Recording Complete: {appointment.title}"

            # Build keywords HTML
            keywords_html = ''
            if recording.keywords:
                keywords_html = '<div style="margin: 15px 0;"><strong>🏷️ Keywords:</strong><br>'
                keywords_html += ', '.join([f'<span style="background: #667eea; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin: 4px;">{k}</span>' for k in recording.keywords])
                keywords_html += '</div>'

            # Build action items HTML
            action_items_html = ''
            if recording.action_items:
                action_items_html = '<div style="margin: 15px 0;"><strong>✅ Action Items:</strong><ul style="margin: 10px 0; padding-left: 20px;">'
                action_items_html += ''.join([f'<li style="margin: 5px 0;">{item}</li>' for item in recording.action_items])
                action_items_html += '</ul></div>'

            # Build topics HTML
            topics_html = ''
            if recording.topics:
                topics_html = '<div style="margin: 15px 0;"><strong>💡 Topics Discussed:</strong><br>'
                topics_html += ', '.join([f'<span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin: 4px;">{t}</span>' for t in recording.topics])
                topics_html += '</div>'

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .success-badge {{
                        background: #10B981;
                        color: white;
                        padding: 12px 24px;
                        border-radius: 50px;
                        font-size: 16px;
                        font-weight: bold;
                        display: inline-block;
                    }}
                    .summary-box {{
                        background: #F3F4F6;
                        padding: 20px;
                        border-radius: 12px;
                        margin: 20px 0;
                        border-left: 4px solid #667eea;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div style="font-size: 32px; font-weight: bold; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                            🤖 Voicebot AI
                        </div>
                        <div style="font-size: 64px; margin: 20px 0;">✅</div>
                        <div class="success-badge">Recording Complete</div>
                    </div>

                    <div style="text-align: center; margin: 20px 0;">
                        <h2 style="color: #333; margin: 0;">{appointment.title}</h2>
                        <p style="color: #666; margin: 10px 0;">
                            {appointment.start_time.strftime('%B %d, %Y at %I:%M %p')}
                        </p>
                    </div>

                    <div class="summary-box">
                        <h3 style="color: #667eea; margin-top: 0;">📝 AI-Generated Summary</h3>
                        <p style="line-height: 1.6; color: #333;">{recording.summary or 'Processing complete. Summary available in your conversation.'}</p>
                    </div>

                    {keywords_html}
                    {action_items_html}
                    {topics_html}

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/chat/?conversation={appointment.conversation_id}"
                           style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 16px 40px; border-radius: 12px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
                            💬 View Full Conversation
                        </a>
                    </div>

                    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 14px;">
                        <p>This is an automated email from Voicebot AI</p>
                        <p>Powered by Voicebot AI 🤖</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send email via Brevo
            api_key = getattr(settings, 'BREVO_API_KEY', None)
            if not api_key:
                logger.error("BREVO_API_KEY not configured")
                return False

            url = 'https://api.brevo.com/v3/smtp/email'
            headers = {
                'accept': 'application/json',
                'api-key': api_key,
                'content-type': 'application/json'
            }

            data = {
                'sender': {
                    'name': 'Voicebot AI',
                    'email': getattr(settings, 'BREVO_SENDER_EMAIL', 'noreply@voicebotai.com')
                },
                'to': [{'email': appointment.user_email}],
                'subject': subject,
                'htmlContent': html_content
            }

            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 201:
                logger.info(f"Sent completion summary email for appointment: {appointment_id}")
                return True
            else:
                logger.error(f"Failed to send completion summary email: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending completion summary email: {str(e)}")
            return False
