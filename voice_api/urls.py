from django.urls import path
from .views import (
    VoiceUploadView, VoiceRequestDetailView, VoiceRequestListView,
    SendOTPView, VerifyOTPView, CheckSessionView, LogoutView,
    SendChatMessageView, ChatHistoryView,
    ConversationsListView, ConversationDetailView, NewConversationView,
    SendChatMessageModernView, GenerateSummaryView, AskContextQuestionView,
    GetContextQuestionsView
)
from .calendar_views import (
    CalendarAppointmentListView, CalendarAppointmentDetailView,
    CancelAppointmentView, UpcomingAppointmentsView,
    UploadAppointmentRecordingView, AppointmentRecordingDetailView,
    RecordingsSummaryView, SendAppointmentReminderView,
    AppointmentNotificationsView, SendConversationLinkEmailView
)

app_name = 'voice_api'

urlpatterns = [
    # Original voice API endpoints
    path('upload/', VoiceUploadView.as_view(), name='voice-upload'),
    path('request/<uuid:request_id>/', VoiceRequestDetailView.as_view(), name='voice-request-detail'),
    path('requests/', VoiceRequestListView.as_view(), name='voice-request-list'),

    # OTP authentication endpoints
    path('auth/send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/check-session/', CheckSessionView.as_view(), name='check-session'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    # Original chat endpoints (for backward compatibility)
    path('chat/send/', SendChatMessageModernView.as_view(), name='send-chat-message'),
    path('chat/history/', ChatHistoryView.as_view(), name='chat-history'),

    # New modern UI endpoints
    path('chat/conversations/', ConversationsListView.as_view(), name='conversations-list'),
    path('chat/conversation/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('chat/new/', NewConversationView.as_view(), name='new-conversation'),

    # Summary and context question endpoints
    path('chat/summary/', GenerateSummaryView.as_view(), name='generate-summary'),
    path('chat/context/question/', AskContextQuestionView.as_view(), name='ask-context-question'),
    path('chat/context/questions/', GetContextQuestionsView.as_view(), name='get-context-questions'),

    # Calendar appointment endpoints
    path('calendar/appointments/', CalendarAppointmentListView.as_view(), name='calendar-appointments-list'),
    path('calendar/appointment/<uuid:appointment_id>/', CalendarAppointmentDetailView.as_view(), name='calendar-appointment-detail'),
    path('calendar/appointment/<uuid:appointment_id>/cancel/', CancelAppointmentView.as_view(), name='cancel-appointment'),
    path('calendar/appointments/upcoming/', UpcomingAppointmentsView.as_view(), name='upcoming-appointments'),

    # Appointment recording endpoints
    path('calendar/appointment/<uuid:appointment_id>/recording/upload/', UploadAppointmentRecordingView.as_view(), name='upload-appointment-recording'),
    path('calendar/appointment/<uuid:appointment_id>/recording/', AppointmentRecordingDetailView.as_view(), name='appointment-recording-detail'),
    path('calendar/recordings/summary/', RecordingsSummaryView.as_view(), name='recordings-summary'),

    # Reminder endpoint
    path('calendar/appointment/<uuid:appointment_id>/reminder/', SendAppointmentReminderView.as_view(), name='send-appointment-reminder'),

    # In-app notifications endpoint
    path('calendar/notifications/', AppointmentNotificationsView.as_view(), name='appointment-notifications'),

    # Send conversation link email
    path('calendar/appointment/send-conversation-link/', SendConversationLinkEmailView.as_view(), name='send-conversation-link-email'),
]