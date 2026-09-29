from django.contrib import admin

from .models import (
    AuditEvent, CaneQualityTest, Delivery, ExternalIdentity, Farm, Farmer,
    FarmExpense, FinanceOffer, FinanceRequest, IntegrationConnection,
    IntegrationEvent, Mill, PricingAssessment, Profile, Receivable,
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


@admin.register(ExternalIdentity)
class ExternalIdentityAdmin(admin.ModelAdmin):
    list_display = ("external_identifier", "source_system", "entity_type", "verified")
    list_filter = ("source_system", "entity_type", "verified")
    search_fields = ("external_identifier", "source_system", "identifier_type")


@admin.register(CaneQualityTest)
class CaneQualityTestAdmin(admin.ModelAdmin):
    list_display = ("delivery", "source_system", "pol_percent", "brix_percent", "tested_at")
    search_fields = ("delivery__reference", "external_reference")


@admin.register(PricingAssessment)
class PricingAssessmentAdmin(admin.ModelAdmin):
    list_display = ("delivery", "calculated_price_per_tonne", "expected_net_value", "mill_declared_net_value", "status")
    list_filter = ("status", "source_system")
    search_fields = ("delivery__reference", "pricing_reference")


@admin.register(FarmExpense)
class FarmExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "farmer", "farm", "category", "amount")
    list_filter = ("category", "expense_date")
    search_fields = ("farmer__farmer_number", "farm__farm_code", "description", "external_reference")


for model in [
    Mill, Farm, Delivery, Receivable, FinanceRequest, FinanceOffer,
    ReceivableAssignment, Settlement, IntegrationConnection, IntegrationEvent,
    AuditEvent,
]:
    admin.site.register(model)
