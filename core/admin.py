from django.contrib import admin
from .models import *
for model in [Profile, Farmer, Mill, Farm, Delivery, Receivable, FinanceRequest, FinanceOffer, ReceivableAssignment, Settlement, IntegrationConnection, IntegrationEvent, AuditEvent]:
    admin.site.register(model)
