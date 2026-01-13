"""
Сервіси для інтеграції з HubSpot API
"""
import logging
from typing import Dict, Optional, Any
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate
from hubspot.crm.deals import SimplePublicObjectInputForCreate as DealInputForCreate
from hubspot.crm.contacts.exceptions import ApiException as ContactApiException
from hubspot.crm.deals.exceptions import ApiException as DealApiException
import os

logger = logging.getLogger(__name__)


class HubSpotService:
    """Сервіс для роботи з HubSpot API"""
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Ініціалізація HubSpot клієнта
        
        Args:
            access_token: HubSpot access token. Якщо не вказано, береться з змінних оточення
        """
        self.access_token = access_token or os.getenv('HUBSPOT_ACCESS_TOKEN')
        if not self.access_token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN не вказано в змінних оточення")
        
        self.client = HubSpot(access_token=self.access_token)
    
    def create_contact(self, email: str, firstname: Optional[str] = None, 
                      lastname: Optional[str] = None, phone: Optional[str] = None,
                      company: Optional[str] = None, **kwargs) -> Optional[str]:
        """
        Створює контакт в HubSpot
        
        Args:
            email: Email контакту (обов'язкове)
            firstname: Ім'я
            lastname: Прізвище
            phone: Телефон
            company: Компанія
            **kwargs: Інші властивості контакту
        
        Returns:
            ID створеного контакту або None у разі помилки
        """
        try:
            properties = {"email": email}
            
            if firstname:
                properties["firstname"] = firstname
            if lastname:
                properties["lastname"] = lastname
            if phone:
                properties["phone"] = phone
            if company:
                properties["company"] = company
            
            # Додаємо додаткові властивості
            properties.update(kwargs)
            
            contact_input = SimplePublicObjectInputForCreate(properties=properties)
            contact = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=contact_input
            )
            
            logger.info(f"Контакт створено в HubSpot: {contact.id}, email: {email}")
            return contact.id
            
        except ContactApiException as e:
            logger.error(f"Помилка створення контакту в HubSpot: {e}")
            if e.status == 409:  # Контакт вже існує
                logger.info(f"Контакт з email {email} вже існує")
                # Можна спробувати знайти існуючий контакт
                return self._find_contact_by_email(email)
            return None
    
    def _find_contact_by_email(self, email: str) -> Optional[str]:
        """Знаходить контакт за email"""
        try:
            from hubspot.crm.contacts import PublicObjectSearchRequest
            
            # Використовуємо search API для пошуку контакту
            search_request = PublicObjectSearchRequest(
                filter_groups=[{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }],
                properties=["email"],
                limit=1
            )
            
            search_result = self.client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )
            
            if search_result.results:
                return search_result.results[0].id
            return None
        except Exception as e:
            logger.error(f"Помилка пошуку контакту: {e}")
            return None
    
    def create_deal(self, dealname: str, amount: Optional[str] = None,
                   closedate: Optional[str] = None, dealstage: str = "appointmentscheduled",
                   pipeline: str = "default", contact_id: Optional[str] = None,
                   **kwargs) -> Optional[str]:
        """
        Створює deal в HubSpot
        
        Args:
            dealname: Назва deal
            amount: Сума
            closedate: Дата закриття (формат: YYYY-MM-DD)
            dealstage: Стадія deal
            pipeline: Pipeline
            contact_id: ID контакту для асоціації
            **kwargs: Інші властивості deal
        
        Returns:
            ID створеного deal або None у разі помилки
        """
        try:
            properties = {"dealname": dealname}
            
            if amount:
                properties["amount"] = str(amount)
            if closedate:
                properties["closedate"] = closedate
            if dealstage:
                properties["dealstage"] = dealstage
            if pipeline:
                properties["pipeline"] = pipeline
            
            # Додаємо додаткові властивості
            properties.update(kwargs)
            
            deal_input = DealInputForCreate(properties=properties)
            deal = self.client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=deal_input
            )
            
            logger.info(f"Deal створено в HubSpot: {deal.id}, назва: {dealname}")
            
            # Асоціюємо з контактом, якщо вказано
            if contact_id:
                self._associate_deal_to_contact(deal.id, contact_id)
            
            return deal.id
            
        except DealApiException as e:
            logger.error(f"Помилка створення deal в HubSpot: {e}")
            return None
    
    def _associate_deal_to_contact(self, deal_id: str, contact_id: str):
        """Асоціює deal з контактом"""
        try:
            from hubspot.crm.associations.v4 import BatchInputPublicAssociationMultiPost
            
            association_input = BatchInputPublicAssociationMultiPost(
                inputs=[{
                    "from": {"id": contact_id},
                    "to": {"id": deal_id},
                    "types": [{
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 4  # CONTACT_TO_DEAL
                    }]
                }]
            )
            
            self.client.crm.associations.v4.batch_api.create(
                from_object_type="contacts",
                to_object_type="deals",
                batch_input_public_association_multi_post=association_input
            )
            
            logger.info(f"Deal {deal_id} асоційовано з контактом {contact_id}")
        except Exception as e:
            logger.error(f"Помилка асоціації deal з контактом: {e}")
    
    def process_gigradar_opportunity(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обробляє дані opportunity з Gigradar і створює контакт та deal в HubSpot
        
        Args:
            opportunity_data: Дані opportunity з webhook Gigradar
        
        Returns:
            Словник з результатами обробки
        """
        result = {
            "success": False,
            "contact_id": None,
            "deal_id": None,
            "errors": []
        }
        
        try:
            # Витягуємо дані з opportunity
            job = opportunity_data.get("job", {})
            job_id = opportunity_data.get("jobId", "")
            opportunity_id = opportunity_data.get("id", "")
            
            # Створюємо контакт (якщо є email клієнта)
            client_email = job.get("client", {}).get("email") or job.get("clientEmail")
            if client_email:
                contact_id = self.create_contact(
                    email=client_email,
                    firstname=job.get("client", {}).get("name") or job.get("clientName"),
                    company=job.get("client", {}).get("company") or job.get("companyName"),
                )
                result["contact_id"] = contact_id
            else:
                # Якщо немає email, створюємо контакт з назвою компанії
                company_name = job.get("client", {}).get("company") or job.get("companyName") or "Unknown Company"
                # Для HubSpot потрібен email, тому використовуємо заглушку
                contact_id = self.create_contact(
                    email=f"{company_name.lower().replace(' ', '_')}@gigradar.placeholder",
                    company=company_name,
                )
                result["contact_id"] = contact_id
            
            # Створюємо deal
            deal_name = f"GigRadar Opportunity: {job.get('title', 'Untitled Job')}"
            budget = job.get("budget") or job.get("hourlyRate")
            
            deal_id = self.create_deal(
                dealname=deal_name,
                amount=str(budget) if budget else None,
                dealstage="appointmentscheduled",
                contact_id=contact_id,
                # Додаткові поля
                gigradar_opportunity_id=opportunity_id,
                gigradar_job_id=job_id,
                job_title=job.get("title", ""),
                job_description=job.get("description", "")[:500],  # Обмежуємо довжину
            )
            
            result["deal_id"] = deal_id
            result["success"] = bool(deal_id)
            
        except Exception as e:
            logger.error(f"Помилка обробки opportunity: {e}")
            result["errors"].append(str(e))
        
        return result
