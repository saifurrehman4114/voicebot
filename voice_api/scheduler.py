"""
Automatic appointment scheduler for reminders and recordings
Runs every minute to check for pending appointments
"""

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from voice_api.services.calendar_service import CalendarService
from voice_api.services.appointment_recording_service import AppointmentRecordingService
import logging

logger = logging.getLogger(__name__)

scheduler = None


def process_appointments():
    """
    Main function to process appointments
    Called every minute by the scheduler
    """
    try:
        logger.info("🔄 Processing appointments...")

        # 1. Send reminders
        send_reminders()

        # 2. Start recordings (auto-create conversation and email link)
        start_recordings()

        # 3. Stop recordings and prepare for processing
        stop_recordings()

        logger.info("✓ Appointment processing completed")

    except Exception as e:
        logger.error(f"✗ Error in process_appointments: {str(e)}")


def send_reminders():
    """Send reminder notifications for upcoming appointments"""
    try:
        appointments = CalendarService.get_appointments_needing_reminders()
        count = 0

        for appointment in appointments:
            try:
                success = CalendarService.send_reminder(appointment.id)
                if success:
                    count += 1
                    logger.info(f"✓ Sent reminder for: {appointment.title} (ID: {appointment.id})")
                else:
                    logger.warning(f"⚠ Failed to send reminder for: {appointment.title}")
            except Exception as e:
                logger.error(f"✗ Error sending reminder for appointment {appointment.id}: {str(e)}")

        if count > 0:
            logger.info(f"📧 Sent {count} reminder(s)")

    except Exception as e:
        logger.error(f"✗ Error in send_reminders: {str(e)}")


def start_recordings():
    """Start recordings for appointments that should be recording now"""
    try:
        appointments = CalendarService.get_appointments_to_start_recording()
        count = 0

        for appointment in appointments:
            try:
                # Get or create ONE conversation for this appointment (reuse from reminder if exists)
                conversation = CalendarService.create_appointment_conversation(appointment.id)
                logger.info(f"   → Using conversation: {conversation.id}")

                # Check if recording already exists
                existing_recording = AppointmentRecordingService.get_recording_by_appointment(appointment.id)
                if existing_recording:
                    logger.warning(f"   → Recording already exists for appointment {appointment.id}, skipping")
                    continue

                # Create recording instance
                recording = AppointmentRecordingService.start_recording(appointment.id)

                # Send email with conversation link (only if not sent before)
                if not appointment.conversation_link_sent:
                    CalendarService.send_recording_started_email(appointment.id, conversation.id)

                count += 1
                logger.info(f"✓ Started recording for: {appointment.title} (ID: {appointment.id})")
                logger.info(f"   → Recording: {recording.id}")

            except Exception as e:
                logger.error(f"✗ Error starting recording for appointment {appointment.id}: {str(e)}")

        if count > 0:
            logger.info(f"🎙️ Started {count} recording(s)")

    except Exception as e:
        logger.error(f"✗ Error in start_recordings: {str(e)}")


def stop_recordings():
    """Stop recordings for appointments that should have ended and process them"""
    try:
        appointments = CalendarService.get_appointments_to_stop_recording()
        count = 0

        for appointment in appointments:
            try:
                # Get the recording
                recording = AppointmentRecordingService.get_recording_by_appointment(appointment.id)

                if recording and recording.recording_status == 'recording':
                    # Mark recording as ready for processing
                    recording.recording_status = 'processing'
                    recording.recording_ended_at = timezone.now()

                    # Calculate duration
                    duration = recording.recording_ended_at - recording.recording_started_at
                    recording.duration_seconds = int(duration.total_seconds())
                    recording.save()

                    # Update appointment status
                    appointment.status = 'completed'
                    appointment.save()

                    count += 1
                    logger.info(f"⏹️ Stopped recording for: {appointment.title} (ID: {appointment.id})")
                    logger.info(f"   → Duration: {recording.duration_seconds}s")
                    logger.info(f"   → Status: Processing (waiting for audio upload)")

            except Exception as e:
                logger.error(f"✗ Error stopping recording for appointment {appointment.id}: {str(e)}")

        if count > 0:
            logger.info(f"🛑 Stopped {count} recording(s)")

    except Exception as e:
        logger.error(f"✗ Error in stop_recordings: {str(e)}")


def start_scheduler():
    """Initialize and start the background scheduler"""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running")
        return

    scheduler = BackgroundScheduler()

    # Run appointment processor every minute
    scheduler.add_job(
        process_appointments,
        'interval',
        minutes=1,
        id='appointment_processor',
        name='Process Appointments',
        replace_existing=True
    )

    scheduler.start()
    logger.info("✓ Appointment scheduler started (runs every minute)")


def stop_scheduler():
    """Stop the scheduler (useful for testing)"""
    global scheduler

    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler stopped")
