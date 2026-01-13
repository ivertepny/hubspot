from django.db import models
from django.utils import timezone
import json


class GigradarProposal(models.Model):
    """
    Модель для збереження proposal подій від Gigradar
    """
    # Основні ідентифікатори
    proposal_id = models.CharField(max_length=255, unique=True, db_index=True, help_text="ID proposal з Gigradar")
    opportunity_id = models.CharField(max_length=255, db_index=True, help_text="ID opportunity")
    job_id = models.CharField(max_length=255, db_index=True, null=True, blank=True, help_text="ID job з Upwork")
    
    # Статуси та дати
    status = models.CharField(max_length=100, null=True, blank=True, help_text="Статус proposal")
    sent_at = models.DateTimeField(null=True, blank=True, help_text="Дата відправки proposal")
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="Запланована дата відправки")
    created_at = models.DateTimeField(null=True, blank=True, help_text="Дата створення в Gigradar")
    
    # Помилки
    has_error = models.BooleanField(default=False, help_text="Чи є помилка при відправці")
    error_code = models.CharField(max_length=100, null=True, blank=True, help_text="Код помилки")
    error_message = models.TextField(null=True, blank=True, help_text="Повідомлення про помилку")
    
    # Додаткова інформація
    scanner_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID scanner")
    scanner_name = models.CharField(max_length=255, null=True, blank=True, help_text="Назва scanner")
    team_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID team")
    team_name = models.CharField(max_length=255, null=True, blank=True, help_text="Назва team")
    
    # Дані про job
    job_title = models.CharField(max_length=500, null=True, blank=True, help_text="Назва job")
    job_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Бюджет job")
    job_type = models.CharField(max_length=50, null=True, blank=True, help_text="Тип job (hourly/fixed)")
    
    # Дані про клієнта
    client_email = models.EmailField(null=True, blank=True, db_index=True, help_text="Email клієнта")
    client_name = models.CharField(max_length=255, null=True, blank=True, help_text="Ім'я клієнта")
    client_company = models.CharField(max_length=255, null=True, blank=True, help_text="Компанія клієнта")
    
    # HubSpot інтеграція
    hubspot_contact_id = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="ID контакту в HubSpot")
    hubspot_deal_id = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="ID deal в HubSpot")
    
    # Повні дані з webhook (JSON)
    raw_data = models.JSONField(default=dict, help_text="Повні дані з webhook у форматі JSON")
    
    # Метадані
    created = models.DateTimeField(auto_now_add=True, help_text="Дата створення запису в БД")
    updated = models.DateTimeField(auto_now=True, help_text="Дата останнього оновлення")
    
    class Meta:
        verbose_name = "Gigradar Proposal"
        verbose_name_plural = "Gigradar Proposals"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['proposal_id']),
            models.Index(fields=['opportunity_id']),
            models.Index(fields=['job_id']),
            models.Index(fields=['client_email']),
            models.Index(fields=['-created']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Proposal {self.proposal_id} - {self.job_title or 'N/A'}"
    
    @classmethod
    def create_from_webhook_data(cls, data: dict) -> 'GigradarProposal':
        """
        Створює або оновлює proposal з даних webhook
        
        Args:
            data: Дані з webhook події GIGRADAR.PROPOSAL.UPDATE
        
        Returns:
            GigradarProposal instance
        """
        # Витягуємо основні дані
        proposal_id = data.get('id') or data.get('proposalId') or data.get('_id')
        if not proposal_id:
            raise ValueError("Proposal ID не знайдено в даних")
        
        # Отримуємо або створюємо proposal
        proposal, created = cls.objects.get_or_create(
            proposal_id=proposal_id,
            defaults={}
        )
        
        # Оновлюємо поля
        proposal.opportunity_id = data.get('opportunityId') or data.get('opportunity_id') or ''
        proposal.job_id = data.get('jobId') or data.get('job_id') or ''
        
        # Статуси та дати
        if 'sent' in data:
            try:
                from django.utils.dateparse import parse_datetime
                proposal.sent_at = parse_datetime(data['sent']) if isinstance(data['sent'], str) else data['sent']
            except:
                pass
        
        if 'scheduledAt' in data:
            try:
                from django.utils.dateparse import parse_datetime
                proposal.scheduled_at = parse_datetime(data['scheduledAt']) if isinstance(data['scheduledAt'], str) else data['scheduledAt']
            except:
                pass
        
        if 'createdAt' in data or 'created_at' in data:
            try:
                from django.utils.dateparse import parse_datetime
                created_date = data.get('createdAt') or data.get('created_at')
                proposal.created_at = parse_datetime(created_date) if isinstance(created_date, str) else created_date
            except:
                pass
        
        # Помилки
        proposal.has_error = data.get('error', False) or data.get('hasError', False)
        proposal.error_code = data.get('errorCode') or data.get('error_code')
        proposal.error_message = data.get('errorMessage') or data.get('error_message')
        
        # Scanner та team
        proposal.scanner_id = data.get('scannerId') or data.get('scanner_id')
        proposal.scanner_name = data.get('scannerName') or data.get('scanner_name')
        proposal.team_id = data.get('teamId') or data.get('team_id')
        proposal.team_name = data.get('teamName') or data.get('team_name')
        
        # Дані про job
        job = data.get('job', {})
        if isinstance(job, dict):
            proposal.job_title = job.get('title') or job.get('jobTitle')
            budget = job.get('budget') or job.get('hourlyRate') or job.get('fixedPrice')
            if budget:
                try:
                    proposal.job_budget = float(budget)
                except:
                    pass
            proposal.job_type = job.get('type') or job.get('jobType')
            
            # Дані про клієнта
            client = job.get('client', {})
            if isinstance(client, dict):
                proposal.client_email = client.get('email')
                proposal.client_name = client.get('name')
                proposal.client_company = client.get('company')
            else:
                # Якщо client - це просто рядок
                proposal.client_email = job.get('clientEmail')
                proposal.client_name = job.get('clientName')
                proposal.client_company = job.get('companyName')
        
        # Зберігаємо повні дані
        proposal.raw_data = data
        
        proposal.save()
        return proposal
