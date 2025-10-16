from django.urls import path
from .views import VoiceUploadView, VoiceRequestDetailView, VoiceRequestListView

app_name = 'voice_api'

urlpatterns = [
    path('upload/', VoiceUploadView.as_view(), name='voice-upload'),
    path('request/<uuid:request_id>/', VoiceRequestDetailView.as_view(), name='voice-request-detail'),
    path('requests/', VoiceRequestListView.as_view(), name='voice-request-list'),
]