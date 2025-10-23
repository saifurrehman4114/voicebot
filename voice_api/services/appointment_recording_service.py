"""
Appointment Recording Service for automatic recording and analysis
File: voice_api/services/appointment_recording_service.py
"""

from django.utils import timezone
from voice_api.models import CalendarAppointment, AppointmentRecording
from voice_api.services.speech_to_text_service import SpeechToTextService
from voice_api.services.intent_classifier_service import IntentClassifierService
from voice_api.services.entity_extraction_service import EntityExtractionService
import logging
import os

logger = logging.getLogger(__name__)


class AppointmentRecordingService:
    """Service for managing appointment recordings and analysis"""

    @staticmethod
    def start_recording(appointment_id):
        """
        Start recording for an appointment

        Args:
            appointment_id: UUID of appointment

        Returns:
            AppointmentRecording instance
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Create recording instance
            recording = AppointmentRecording.objects.create(
                appointment=appointment,
                recording_status='recording',
                recording_started_at=timezone.now()
            )

            # Update appointment status
            appointment.status = 'recording'
            appointment.save()

            logger.info(f"Started recording for appointment: {appointment_id}")
            return recording

        except CalendarAppointment.DoesNotExist:
            logger.error(f"Appointment not found: {appointment_id}")
            raise
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
            raise

    @staticmethod
    def stop_recording(recording_id, audio_file_path):
        """
        Stop recording and save audio file

        Args:
            recording_id: UUID of recording
            audio_file_path: Path to saved audio file

        Returns:
            Updated AppointmentRecording instance
        """
        try:
            recording = AppointmentRecording.objects.get(id=recording_id)

            # Get file information
            if os.path.exists(audio_file_path):
                file_size = os.path.getsize(audio_file_path)
                file_format = os.path.splitext(audio_file_path)[1].lstrip('.')
            else:
                file_size = 0
                file_format = 'unknown'

            # Calculate duration
            recording_ended_at = timezone.now()
            duration = recording_ended_at - recording.recording_started_at
            duration_seconds = int(duration.total_seconds())

            # Update recording
            recording.audio_file = audio_file_path
            recording.file_size = file_size
            recording.file_format = file_format
            recording.recording_ended_at = recording_ended_at
            recording.duration_seconds = duration_seconds
            recording.recording_status = 'processing'
            recording.save()

            logger.info(f"Stopped recording: {recording_id}")
            return recording

        except AppointmentRecording.DoesNotExist:
            logger.error(f"Recording not found: {recording_id}")
            raise
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            raise

    @staticmethod
    def process_recording(recording_id):
        """
        Process recording: transcribe, analyze, and generate summary

        Args:
            recording_id: UUID of recording

        Returns:
            Updated AppointmentRecording instance
        """
        try:
            recording = AppointmentRecording.objects.get(id=recording_id)

            if not recording.audio_file:
                raise ValueError("No audio file to process")

            # Step 1: Transcribe audio
            logger.info(f"Transcribing recording: {recording_id}")
            speech_service = SpeechToTextService()
            transcription_result = speech_service.transcribe_audio(recording.audio_file)

            if transcription_result['status'] == 'success':
                recording.transcribed_text = transcription_result['text']
            else:
                recording.recording_status = 'failed'
                recording.error_message = transcription_result.get('error', 'Transcription failed')
                recording.save()
                return recording

            # Step 2: Classify intent
            logger.info(f"Classifying intent for recording: {recording_id}")
            intent_service = IntentClassifierService()
            intent_result = intent_service.classify_intent(recording.transcribed_text)

            if intent_result['status'] == 'success':
                recording.intent = intent_result['intent']
                recording.intent_confidence = intent_result['confidence']
                # Use intent summary as the meeting summary initially
                recording.summary = intent_result.get('summary', '')
            else:
                logger.warning(f"Intent classification failed for recording: {recording_id}")

            # Step 3: Extract entities
            logger.info(f"Extracting entities for recording: {recording_id}")
            entity_service = EntityExtractionService()
            entity_result = entity_service.extract_entities(recording.transcribed_text)

            if entity_result['status'] == 'success':
                recording.keywords = entity_result.get('keywords', [])
                recording.entities = entity_result.get('entities', [])
                recording.domain_terms = entity_result.get('domain_terms', [])
                recording.action_items = entity_result.get('action_items', [])
                recording.topics = entity_result.get('topics', [])
            else:
                logger.warning(f"Entity extraction failed for recording: {recording_id}")

            # Step 4: Generate detailed summary using Groq
            logger.info(f"Generating summary for recording: {recording_id}")
            try:
                from groq import Groq
                groq_api_key = os.getenv('GROQ_API_KEY')

                if groq_api_key:
                    client = Groq(api_key=groq_api_key)

                    system_prompt = """You are an AI assistant that creates comprehensive meeting summaries.
                    Generate a detailed summary of the meeting that includes:
                    1. Main topics discussed
                    2. Key decisions made
                    3. Action items and next steps
                    4. Important points mentioned
                    Keep the summary clear, structured, and professional."""

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",  # Updated to current model
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Generate a comprehensive summary of this meeting:\n\n{recording.transcribed_text}"}
                        ],
                        temperature=0.5,
                        max_tokens=500
                    )

                    recording.summary = response.choices[0].message.content

            except Exception as e:
                logger.error(f"Error generating summary: {str(e)}")
                # Keep the intent summary if detailed summary fails

            # Mark as completed
            recording.recording_status = 'completed'
            recording.processed_at = timezone.now()
            recording.save()

            # Update appointment status
            recording.appointment.status = 'completed'
            recording.appointment.save()

            # Send completion email with summary
            try:
                from voice_api.services.calendar_service import CalendarService
                CalendarService.send_completion_summary_email(recording.appointment.id, recording)
                logger.info(f"   → Sent completion summary email")
            except Exception as email_error:
                logger.error(f"   → Failed to send completion email: {str(email_error)}")

            logger.info(f"Successfully processed recording: {recording_id}")
            return recording

        except AppointmentRecording.DoesNotExist:
            logger.error(f"Recording not found: {recording_id}")
            raise
        except Exception as e:
            logger.error(f"Error processing recording: {str(e)}")

            # Mark as failed
            try:
                recording = AppointmentRecording.objects.get(id=recording_id)
                recording.recording_status = 'failed'
                recording.error_message = str(e)
                recording.save()
            except:
                pass

            raise

    @staticmethod
    def get_recording_by_appointment(appointment_id):
        """
        Get recording for an appointment

        Args:
            appointment_id: UUID of appointment

        Returns:
            AppointmentRecording instance or None
        """
        try:
            return AppointmentRecording.objects.filter(
                appointment_id=appointment_id
            ).order_by('-created_at').first()

        except Exception as e:
            logger.error(f"Error getting recording: {str(e)}")
            return None

    @staticmethod
    def upload_and_process_recording(appointment_id, audio_file):
        """
        Upload an audio file for an appointment and process it

        Args:
            appointment_id: UUID of appointment
            audio_file: Uploaded audio file

        Returns:
            AppointmentRecording instance
        """
        try:
            appointment = CalendarAppointment.objects.get(id=appointment_id)

            # Save audio file
            from django.core.files.storage import default_storage
            import uuid

            file_extension = os.path.splitext(audio_file.name)[1]
            file_name = f"appointment_recordings/{appointment_id}_{uuid.uuid4()}{file_extension}"
            file_path = default_storage.save(file_name, audio_file)

            # Get absolute path
            absolute_path = default_storage.path(file_path)

            # Create recording
            file_size = audio_file.size
            file_format = file_extension.lstrip('.')

            recording = AppointmentRecording.objects.create(
                appointment=appointment,
                audio_file=file_path,
                file_size=file_size,
                file_format=file_format,
                recording_status='processing',
                recording_started_at=timezone.now(),
                recording_ended_at=timezone.now()
            )

            # Process recording
            AppointmentRecordingService.process_recording(recording.id)

            return recording

        except CalendarAppointment.DoesNotExist:
            logger.error(f"Appointment not found: {appointment_id}")
            raise
        except Exception as e:
            logger.error(f"Error uploading and processing recording: {str(e)}")
            raise

    @staticmethod
    def delete_recording(recording_id):
        """
        Delete a recording and its associated file

        Args:
            recording_id: UUID of recording
        """
        try:
            recording = AppointmentRecording.objects.get(id=recording_id)

            # Delete audio file
            if recording.audio_file:
                from django.core.files.storage import default_storage
                if default_storage.exists(recording.audio_file):
                    default_storage.delete(recording.audio_file)

            # Delete recording
            recording.delete()
            logger.info(f"Deleted recording: {recording_id}")

        except AppointmentRecording.DoesNotExist:
            logger.error(f"Recording not found: {recording_id}")
            raise
        except Exception as e:
            logger.error(f"Error deleting recording: {str(e)}")
            raise

    @staticmethod
    def get_recordings_summary(user_email, start_date=None, end_date=None):
        """
        Get summary of all recordings for a user

        Args:
            user_email: User's email address
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            List of recording summaries
        """
        try:
            appointments = CalendarAppointment.objects.filter(user_email=user_email)

            if start_date:
                appointments = appointments.filter(start_time__gte=start_date)
            if end_date:
                appointments = appointments.filter(start_time__lte=end_date)

            summaries = []
            for apt in appointments:
                recording = AppointmentRecording.objects.filter(
                    appointment=apt,
                    recording_status='completed'
                ).first()

                if recording:
                    summaries.append({
                        'appointment_id': str(apt.id),
                        'recording_id': str(recording.id),
                        'title': apt.title,
                        'start_time': apt.start_time,
                        'duration_minutes': apt.duration_minutes,
                        'summary': recording.summary,
                        'intent': recording.intent,
                        'keywords': recording.keywords,
                        'action_items': recording.action_items,
                        'topics': recording.topics
                    })

            return summaries

        except Exception as e:
            logger.error(f"Error getting recordings summary: {str(e)}")
            return []
