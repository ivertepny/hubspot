"""
URL конфігурація для integrations app
"""
from django.urls import path
from integrations.views import GigradarWebhookView, webhook_health_check

app_name = 'integrations'

urlpatterns = [
    path('hooks/catch/<str:webhook_token>/', GigradarWebhookView.as_view(), name='gigradar_webhook'),
    path('webhooks/health', webhook_health_check, name='webhook_health'),
]
