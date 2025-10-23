"""
Management command to process appointments (reminders and recordings)
Run this command periodically (e.g., via cron or systemd timer)

Usage:
    python manage.py process_appointments
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from voice_api.services.calendar_service import CalendarService
from voice_api.services.appointment_recording_service import AppointmentRecordingService
from voice_api.models import CalendarAppointment
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process appointment reminders and recordings'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'Starting appointment processing at {timezone.now()}'))

        # 1. Send reminders for upcoming appointments
        self.send_reminders()

        # 2. Start recordings for appointments that should be recording now
        self.start_recordings()

        # 3. Stop recordings for appointments that should have ended
        self.stop_recordings()

        self.stdout.write(self.style.SUCCESS(f'Completed appointment processing at {timezone.now()}'))

    def send_reminders(self):
        """Send reminder notifications for upcoming appointments"""
        try:
            appointments = CalendarService.get_appointments_needing_reminders()
            count = 0

            for appointment in appointments:
                try:
                    success = CalendarService.send_reminder(appointment.id)
                    if success:
                        count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'✓ Sent reminder for: {appointment.title} (ID: {appointment.id})'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'⚠ Failed to send reminder for: {appointment.title} (ID: {appointment.id})'
                        ))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ Error sending reminder for appointment {appointment.id}: {str(e)}'
                    ))
                    logger.error(f'Error sending reminder for appointment {appointment.id}: {str(e)}')

            self.stdout.write(self.style.SUCCESS(f'Sent {count} reminders'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in send_reminders: {str(e)}'))
            logger.error(f'Error in send_reminders: {str(e)}')

    def start_recordings(self):
        """Start recordings for appointments that should be recording now"""
        try:
            appointments = CalendarService.get_appointments_to_start_recording()
            count = 0

            for appointment in appointments:
                try:
                    # Start recording
                    recording = AppointmentRecordingService.start_recording(appointment.id)

                    # Send recording start notification
                    CalendarService.start_recording_notification(appointment.id)

                    count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Started recording for: {appointment.title} (ID: {appointment.id})'
                    ))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ Error starting recording for appointment {appointment.id}: {str(e)}'
                    ))
                    logger.error(f'Error starting recording for appointment {appointment.id}: {str(e)}')

            self.stdout.write(self.style.SUCCESS(f'Started {count} recordings'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in start_recordings: {str(e)}'))
            logger.error(f'Error in start_recordings: {str(e)}')

    def stop_recordings(self):
        """Stop recordings for appointments that should have ended"""
        try:
            appointments = CalendarService.get_appointments_to_stop_recording()
            count = 0

            for appointment in appointments:
                try:
                    # Get the recording
                    recording = AppointmentRecordingService.get_recording_by_appointment(appointment.id)

                    if recording and recording.recording_status == 'recording':
                        # In a real implementation, you would:
                        # 1. Stop the actual audio recording (hardware/software integration)
                        # 2. Save the audio file
                        # 3. Call stop_recording with the file path

                        # For now, we'll mark it as ready for manual upload
                        recording.recording_status = 'pending'
                        recording.recording_ended_at = timezone.now()
                        recording.save()

                        # Update appointment status
                        appointment.status = 'completed'
                        appointment.save()

                        count += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'✓ Stopped recording for: {appointment.title} (ID: {appointment.id})'
                        ))
                        self.stdout.write(self.style.WARNING(
                            f'  → Recording marked as pending upload. User can manually upload the audio file.'
                        ))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ Error stopping recording for appointment {appointment.id}: {str(e)}'
                    ))
                    logger.error(f'Error stopping recording for appointment {appointment.id}: {str(e)}')

            self.stdout.write(self.style.SUCCESS(f'Stopped {count} recordings'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error in stop_recordings: {str(e)}'))
            logger.error(f'Error in stop_recordings: {str(e)}')
