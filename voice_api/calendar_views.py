"""
Calendar API Views for appointment management
File: voice_api/calendar_views.py
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from voice_api.models import CalendarAppointment, AppointmentRecording
from voice_api.serializers import (
    CalendarAppointmentSerializer,
    CreateAppointmentSerializer,
    AppointmentRecordingSerializer,
    UploadRecordingSerializer
)
from voice_api.services.calendar_service import CalendarService
from voice_api.services.appointment_recording_service import AppointmentRecordingService
import logging

logger = logging.getLogger(__name__)


class CalendarAppointmentListView(APIView):
    """
    GET: List all appointments for a user
    POST: Create a new appointment
    """

    def get(self, request):
        """Get all appointments for the user"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Get query parameters
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            appointment_status = request.query_params.get('status')

            # Parse dates if provided
            if start_date:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            # Get appointments
            appointments = CalendarService.get_appointments(
                user_email=user_email,
                start_date=start_date,
                end_date=end_date,
                status=appointment_status
            )

            serializer = CalendarAppointmentSerializer(appointments, many=True)
            return Response({
                'appointments': serializer.data,
                'count': len(serializer.data)
            })

        except Exception as e:
            logger.error(f"Error getting appointments: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create a new appointment"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            serializer = CreateAppointmentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create appointment
            appointment = CalendarService.create_appointment(
                user_email=user_email,
                **serializer.validated_data
            )

            response_serializer = CalendarAppointmentSerializer(appointment)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error creating appointment: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CalendarAppointmentDetailView(APIView):
    """
    GET: Get appointment details
    PUT: Update appointment
    DELETE: Delete appointment
    """

    def get(self, request, appointment_id):
        """Get appointment details"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            serializer = CalendarAppointmentSerializer(appointment)
            return Response(serializer.data)

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting appointment: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, appointment_id):
        """Update appointment"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Verify ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Update appointment
            updated_appointment = CalendarService.update_appointment(
                appointment_id=appointment_id,
                **request.data
            )

            serializer = CalendarAppointmentSerializer(updated_appointment)
            return Response(serializer.data)

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating appointment: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, appointment_id):
        """Delete appointment"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Verify ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Delete appointment
            CalendarService.delete_appointment(appointment_id)

            return Response(
                {'message': 'Appointment deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting appointment: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CancelAppointmentView(APIView):
    """POST: Cancel an appointment"""

    def post(self, request, appointment_id):
        """Cancel appointment"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Verify ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Cancel appointment
            cancelled_appointment = CalendarService.cancel_appointment(appointment_id)

            serializer = CalendarAppointmentSerializer(cancelled_appointment)
            return Response(serializer.data)

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error cancelling appointment: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpcomingAppointmentsView(APIView):
    """GET: Get upcoming appointments"""

    def get(self, request):
        """Get upcoming appointments for the next N hours"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Get hours parameter (default 24)
            hours = int(request.query_params.get('hours', 24))

            appointments = CalendarService.get_upcoming_appointments(
                user_email=user_email,
                hours=hours
            )

            serializer = CalendarAppointmentSerializer(appointments, many=True)
            return Response({
                'appointments': serializer.data,
                'count': len(serializer.data)
            })

        except Exception as e:
            logger.error(f"Error getting upcoming appointments: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadAppointmentRecordingView(APIView):
    """POST: Upload and process a recording for an appointment"""

    def post(self, request, appointment_id):
        """Upload recording"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Verify ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Validate file
            serializer = UploadRecordingSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Upload and process recording
            audio_file = request.FILES['audio_file']
            recording = AppointmentRecordingService.upload_and_process_recording(
                appointment_id=appointment_id,
                audio_file=audio_file
            )

            response_serializer = AppointmentRecordingSerializer(recording)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error uploading recording: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRecordingDetailView(APIView):
    """GET: Get recording details"""

    def get(self, request, appointment_id):
        """Get recording for an appointment"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Verify ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Get recording
            recording = AppointmentRecordingService.get_recording_by_appointment(appointment_id)

            if not recording:
                return Response(
                    {'error': 'No recording found for this appointment'},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = AppointmentRecordingSerializer(recording)
            return Response(serializer.data)

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting recording: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecordingsSummaryView(APIView):
    """GET: Get summary of all recordings for a user"""

    def get(self, request):
        """Get recordings summary"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Get date range
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            if start_date:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            # Get summaries
            summaries = AppointmentRecordingService.get_recordings_summary(
                user_email=user_email,
                start_date=start_date,
                end_date=end_date
            )

            return Response({
                'recordings': summaries,
                'count': len(summaries)
            })

        except Exception as e:
            logger.error(f"Error getting recordings summary: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SendAppointmentReminderView(APIView):
    """POST: Manually send reminder for an appointment"""

    def post(self, request, appointment_id):
        """Send reminder"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Verify ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Send reminder
            success = CalendarService.send_reminder(appointment_id)

            if success:
                return Response({'message': 'Reminder sent successfully'})
            else:
                return Response(
                    {'error': 'Failed to send reminder'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentNotificationsView(APIView):
    """GET: Get appointments that need in-app notifications"""

    def get(self, request):
        """Get appointments needing notifications (reminders and start times)"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            now = timezone.now()

            # Get appointments starting in the next 10 minutes OR started within the last 5 minutes
            upcoming_start = now + timedelta(minutes=10)
            recent_start = now - timedelta(minutes=5)

            # Get appointments that need reminders or are about to start or just started
            appointments = CalendarAppointment.objects.filter(
                user_email=user_email,
                start_time__gte=recent_start,
                start_time__lte=upcoming_start,
                status__in=['scheduled', 'reminder_sent']
            ).order_by('start_time')

            notifications = []
            for apt in appointments:
                time_until_start = (apt.start_time - now).total_seconds() / 60

                # Check if it's reminder time (within reminder window)
                reminder_time = apt.start_time - timedelta(minutes=apt.reminder_minutes_before)
                is_reminder_time = now >= reminder_time and not apt.reminder_sent

                # Check if it's start time (within 5 minutes before or 5 minutes after start)
                # Extended window to ensure users don't miss the notification
                is_start_time = -5 <= time_until_start <= 5

                # ALWAYS show start notifications for reminder_sent status within the time window
                if is_reminder_time or is_start_time:
                    notification = {
                        'id': str(apt.id),
                        'title': apt.title,
                        'description': apt.description,
                        'start_time': apt.start_time.isoformat(),
                        'end_time': apt.end_time.isoformat(),
                        'location': apt.location,
                        'color': apt.color,
                        'auto_record': apt.auto_record,
                        'type': 'start' if is_start_time else 'reminder',
                        'minutes_until_start': int(time_until_start),
                        'reminder_sent': apt.reminder_sent,
                        'conversation_id': str(apt.conversation_id) if apt.conversation_id else None
                    }
                    notifications.append(notification)

            return Response({
                'notifications': notifications,
                'count': len(notifications)
            })

        except Exception as e:
            logger.error(f"Error getting appointment notifications: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SendConversationLinkEmailView(APIView):
    """POST: Send email with conversation link when appointment recording starts"""

    def post(self, request):
        """Send conversation link email"""
        try:
            user_email = request.session.get('user_email')
            if not user_email:
                return Response(
                    {'error': 'Not authenticated'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            appointment_id = request.data.get('appointment_id')
            conversation_id = request.data.get('conversation_id')

            if not appointment_id or not conversation_id:
                return Response(
                    {'error': 'Both appointment_id and conversation_id are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify appointment ownership
            appointment = CalendarAppointment.objects.get(
                id=appointment_id,
                user_email=user_email
            )

            # Send email with conversation link
            success = CalendarService.send_conversation_link_email(
                appointment_id=appointment_id,
                conversation_id=conversation_id,
                user_email=user_email
            )

            if success:
                return Response({'message': 'Email sent successfully'})
            else:
                return Response(
                    {'error': 'Failed to send email'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except CalendarAppointment.DoesNotExist:
            return Response(
                {'error': 'Appointment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error sending conversation link email: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
