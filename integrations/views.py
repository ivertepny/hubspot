"""
Views для обробки webhook від Gigradar
"""
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from integrations.services import HubSpotService
from integrations.models import GigradarProposal
import os

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class GigradarWebhookView(View):
    """
    View для обробки webhook подій від Gigradar
    Формат URL: /hooks/catch/<webhook_token>/
    """
    
    def post(self, request, webhook_token):
        """
        Обробляє POST запит від Gigradar webhook
        
        Args:
            webhook_token: Токен з URL для валідації
        
        Очікуваний формат:
        {
            "event": "GIGRADAR.OPPORTUNITY.CREATE",
            "data": {
                "id": "...",
                "jobId": "...",
                "job": {...}
            }
        }
        """
        try:
            # Валідуємо webhook токен
            valid_token = os.getenv('WEBHOOK_TOKEN')
            if valid_token and webhook_token != valid_token:
                logger.warning(f"Невірний webhook токен: {webhook_token}")
                return JsonResponse(
                    {"error": "Invalid webhook token"},
                    status=401
                )
            
            # Парсимо JSON
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError:
                logger.error("Невірний JSON формат в webhook")
                return JsonResponse(
                    {"error": "Invalid JSON format"},
                    status=400
                )
            
            # Перевіряємо базову аутентифікацію (якщо налаштовано, опціонально)
            webhook_username = os.getenv('WEBHOOK_USERNAME')
            webhook_password = os.getenv('WEBHOOK_PASSWORD')
            
            if webhook_username and webhook_password:
                from django.contrib.auth import authenticate
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if not auth_header.startswith('Basic '):
                    return JsonResponse(
                        {"error": "Authentication required"},
                        status=401
                    )
            
            # Отримуємо тип події
            event_type = payload.get("event") or payload.get("type")
            data = payload.get("data") or payload
            
            logger.info(f"Отримано webhook подію: {event_type}")
            
            # Обробляємо різні типи подій
            if event_type == "GIGRADAR.OPPORTUNITY.CREATE":
                return self._handle_opportunity_create(data)
            elif event_type == "GIGRADAR.PROPOSAL.UPDATE" or event_type == "GIGRADAR.PROPOSAL.CREATE":
                return self._handle_proposal_update(data)
            else:
                logger.warning(f"Невідомий тип події: {event_type}")
                # Повертаємо 200 OK, щоб Gigradar не повторював запит
                return JsonResponse({"status": "received", "message": f"Event {event_type} received but not processed"})
        
        except Exception as e:
            logger.error(f"Помилка обробки webhook: {e}", exc_info=True)
            # Повертаємо 200 OK, щоб Gigradar не повторював запит
            # Помилки логуються для подальшого аналізу
            return JsonResponse(
                {"status": "error", "message": "Internal server error"},
                status=200
            )
    
    def _handle_opportunity_create(self, data: dict) -> JsonResponse:
        """
        Обробляє подію створення opportunity
        
        Args:
            data: Дані opportunity з webhook
        """
        try:
            # Ініціалізуємо HubSpot сервіс
            hubspot_service = HubSpotService()
            
            # Обробляємо opportunity
            result = hubspot_service.process_gigradar_opportunity(data)
            
            if result["success"]:
                logger.info(
                    f"Opportunity успішно оброблено. "
                    f"Contact ID: {result['contact_id']}, Deal ID: {result['deal_id']}"
                )
                return JsonResponse({
                    "status": "success",
                    "message": "Opportunity processed successfully",
                    "contact_id": result["contact_id"],
                    "deal_id": result["deal_id"]
                })
            else:
                logger.warning(
                    f"Помилка обробки opportunity: {result.get('errors', [])}"
                )
                return JsonResponse({
                    "status": "partial_success",
                    "message": "Opportunity processed with errors",
                    "errors": result.get("errors", [])
                })
        
        except ValueError as e:
            # Помилка конфігурації (наприклад, відсутній токен)
            logger.error(f"Помилка конфігурації HubSpot: {e}")
            return JsonResponse({
                "status": "error",
                "message": "HubSpot configuration error"
            }, status=200)  # Все одно 200, щоб не повторювати
        
        except Exception as e:
            logger.error(f"Помилка обробки opportunity: {e}", exc_info=True)
            return JsonResponse({
                "status": "error",
                "message": "Failed to process opportunity"
            }, status=200)  # Все одно 200, щоб не повторювати
    
    def _handle_proposal_update(self, data: dict) -> JsonResponse:
        """
        Обробляє подію оновлення/створення proposal
        
        Args:
            data: Дані proposal з webhook
        """
        try:
            # Зберігаємо proposal в базу даних
            proposal = GigradarProposal.create_from_webhook_data(data)
            
            logger.info(
                f"Proposal збережено в БД: {proposal.proposal_id}, "
                f"статус: {proposal.status}, помилка: {proposal.has_error}"
            )
            
            # Можна додати логіку оновлення deal в HubSpot, якщо потрібно
            # Наприклад, оновити статус deal на основі статусу proposal
            
            return JsonResponse({
                "status": "success",
                "message": "Proposal saved successfully",
                "proposal_id": proposal.proposal_id,
                "saved_at": proposal.created.isoformat()
            })
        
        except ValueError as e:
            logger.error(f"Помилка збереження proposal: {e}")
            return JsonResponse({
                "status": "error",
                "message": f"Failed to save proposal: {str(e)}"
            }, status=200)  # Все одно 200, щоб не повторювати
        
        except Exception as e:
            logger.error(f"Помилка обробки proposal: {e}", exc_info=True)
            return JsonResponse({
                "status": "error",
                "message": "Failed to process proposal"
            }, status=200)  # Все одно 200, щоб не повторювати


@csrf_exempt
@require_http_methods(["GET"])
def webhook_health_check(request):
    """
    Health check endpoint для перевірки доступності webhook
    """
    return JsonResponse({
        "status": "ok",
        "service": "Gigradar Webhook Handler"
    })
