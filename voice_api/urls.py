from django.urls import path
from .views import (
    VoiceUploadView, VoiceRequestDetailView, VoiceRequestListView,
    SendOTPView, VerifyOTPView, CheckSessionView, LogoutView,
    SendChatMessageView, ChatHistoryView,
    ConversationsListView, ConversationDetailView, NewConversationView,
    SendChatMessageModernView
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
]