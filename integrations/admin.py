from django.contrib import admin
from integrations.models import GigradarProposal


@admin.register(GigradarProposal)
class GigradarProposalAdmin(admin.ModelAdmin):
    """Admin інтерфейс для GigradarProposal"""
    
    list_display = [
        'proposal_id',
        'job_title',
        'client_email',
        'status',
        'has_error',
        'sent_at',
        'created',
    ]
    
    list_filter = [
        'status',
        'has_error',
        'job_type',
        'created',
        'sent_at',
    ]
    
    search_fields = [
        'proposal_id',
        'opportunity_id',
        'job_id',
        'job_title',
        'client_email',
        'client_name',
        'scanner_name',
    ]
    
    readonly_fields = [
        'proposal_id',
        'created',
        'updated',
        'raw_data',
    ]
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('proposal_id', 'opportunity_id', 'job_id', 'status')
        }),
        ('Дати', {
            'fields': ('sent_at', 'scheduled_at', 'created_at', 'created', 'updated')
        }),
        ('Помилки', {
            'fields': ('has_error', 'error_code', 'error_message')
        }),
        ('Job інформація', {
            'fields': ('job_title', 'job_budget', 'job_type')
        }),
        ('Клієнт', {
            'fields': ('client_email', 'client_name', 'client_company')
        }),
        ('Scanner/Team', {
            'fields': ('scanner_id', 'scanner_name', 'team_id', 'team_name')
        }),
        ('HubSpot інтеграція', {
            'fields': ('hubspot_contact_id', 'hubspot_deal_id')
        }),
        ('Дані', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created'
    
    def get_readonly_fields(self, request, obj=None):
        """Всі поля readonly для існуючих об'єктів"""
        if obj:
            return self.readonly_fields + [
                'proposal_id', 'opportunity_id', 'job_id', 'status',
                'sent_at', 'scheduled_at', 'created_at',
                'has_error', 'error_code', 'error_message',
                'job_title', 'job_budget', 'job_type',
                'client_email', 'client_name', 'client_company',
                'scanner_id', 'scanner_name', 'team_id', 'team_name',
                'hubspot_contact_id', 'hubspot_deal_id',
            ]
        return self.readonly_fields
