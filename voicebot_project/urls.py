from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse

# Simple view to handle Chrome DevTools requests
def chrome_devtools_handler(request):
    return JsonResponse({}, status=200)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/voice/', include('voice_api.urls')),

    # Template routes
    path('', TemplateView.as_view(template_name='otp_verify.html'), name='home'),
    path('chat/', TemplateView.as_view(template_name='chat_copilot.html'), name='chat'),
    path('calendar/', TemplateView.as_view(template_name='calendar.html'), name='calendar'),

    # Chrome DevTools handler (to suppress 404 warnings)
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools_handler),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)