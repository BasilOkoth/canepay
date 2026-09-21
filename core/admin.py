from django.contrib import admin

from .models import (
    AuditEvent, Delivery, Farm, Farmer, FinanceOffer, FinanceRequest,
    IntegrationConnection, IntegrationEvent, Mill, Profile, Receivable,
    ReceivableAssignment, Settlement,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "organisation", "account_status", "phone")
    list_filter = ("role", "account_status")
    search_fields = ("user__username", "user__email", "organisation", "phone")
    list_editable = ("account_status",)


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ("farmer_number", "user", "county", "verified")
    list_filter = ("verified", "county")
    search_fields = ("farmer_number", "ksb_grower_id", "national_id", "user__username", "user__email")


for model in [Mill, Farm, Delivery, Receivable, FinanceRequest, FinanceOffer, ReceivableAssignment, Settlement, IntegrationConnection, IntegrationEvent, AuditEvent]:
    admin.site.register(model)
