from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.views.static import serve
import os

# Simple view to handle Chrome DevTools requests
def chrome_devtools_handler(request):
    return JsonResponse({}, status=200)

# Service Worker view with proper headers
def service_worker_view(request):
    """Serve service worker with Service-Worker-Allowed header"""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response

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
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Service Worker MUST be after static files to override the static handler
urlpatterns += [
    path('sw.js', service_worker_view, name='service-worker'),
]