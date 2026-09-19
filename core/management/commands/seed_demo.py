from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    AuditEvent, Delivery, Farmer, Farm, IntegrationConnection, Mill, Profile, Receivable
)

class Command(BaseCommand):
    help = "Create explicitly labelled Miwa360 demo accounts and sample data."

    def handle(self, *args, **kwargs):
        password = "Demo123!"
        farmer_user, _ = User.objects.get_or_create(username="farmer", defaults={"first_name":"Demo","last_name":"Farmer","email":"farmer@example.com"})
        mill_user, _ = User.objects.get_or_create(username="mill", defaults={"first_name":"Demo","last_name":"Miller"})
        sacco_user, _ = User.objects.get_or_create(username="sacco", defaults={"first_name":"Demo","last_name":"Financier"})
        oversight_user, _ = User.objects.get_or_create(username="oversight", defaults={"first_name":"Demo","last_name":"Oversight"})
        for user in [farmer_user,mill_user,sacco_user,oversight_user]:
            user.set_password(password)
            user.save()

        Profile.objects.update_or_create(user=farmer_user, defaults={"role":"farmer","organisation":"","phone":"0700000001"})
        Profile.objects.update_or_create(user=mill_user, defaults={"role":"mill","organisation":"Demo Sugar Mill","phone":"0700000002"})
        Profile.objects.update_or_create(user=sacco_user, defaults={"role":"financier","organisation":"Demo SACCO","phone":"0700000003"})
        Profile.objects.update_or_create(user=oversight_user, defaults={"role":"regulator","organisation":"Demo Oversight","phone":"0700000004"})

        farmer, _ = Farmer.objects.update_or_create(
            user=farmer_user,
            defaults={"national_id":"DEMO-ID-001","farmer_number":"FRM-DEMO-001","ksb_grower_id":"GROWER-DEMO-001","county":"Kisumu","verified":True}
        )
        mill, _ = Mill.objects.update_or_create(
            code="DML",
            defaults={"name":"Demo Sugar Mill","county":"Kisumu","verified":True,"payment_terms_days":30,"payment_risk":"medium"}
        )
        farm, _ = Farm.objects.update_or_create(
            farm_code="FARM-DEMO-001",
            defaults={"farmer":farmer,"acreage":Decimal("3.20"),"location":"Demo location, Kisumu","variety":"Demo variety"}
        )
        delivery, _ = Delivery.objects.update_or_create(
            reference="MWD-DEMO-0001",
            defaults={
                "farmer":farmer,"farm":farm,"mill":mill,
                "delivered_at":timezone.now()-timedelta(days=4),
                "gross_weight_tonnes":Decimal("18.40"),"accepted_weight_tonnes":Decimal("18.00"),
                "quality_score":Decimal("15.10"),"price_per_tonne":Decimal("5750.00"),
                "deductions":Decimal("4500.00"),"source_system":"manual",
                "delivery_ticket_number":"DEMO-TICKET-001","mill_approved":True,
                "status":"acknowledged","verified_by":mill_user,"verified_at":timezone.now()-timedelta(days=4,hours=-1),
            }
        )
        receivable, _ = Receivable.objects.update_or_create(
            delivery=delivery,
            defaults={
                "reference":"MWR-DEMO-0001","amount":delivery.amount_payable,
                "due_date":timezone.localdate()+timedelta(days=26),
                "mill_acknowledged":True,"acknowledged_by":mill_user,
                "acknowledged_at":timezone.now()-timedelta(days=3),"status":"verified",
            }
        )

        IntegrationConnection.objects.update_or_create(
            code="delivery-api",
            defaults={"name":"Miwa360 Delivery Ingestion API","connection_type":"REST / JSON","status":"sandbox","enabled":True,"data_scope":"Verified cane delivery records from approved external systems"}
        )
        IntegrationConnection.objects.update_or_create(
            code="industry-information-system",
            defaults={"name":"Industry information system connector","connection_type":"REST / open data","status":"planned","enabled":False,"data_scope":"Grower, mill and supply-chain identifiers"}
        )
        IntegrationConnection.objects.update_or_create(
            code="quality-payment-system",
            defaults={"name":"Quality / cane payment data connector","connection_type":"REST / data exchange","status":"planned","enabled":False,"data_scope":"Quality and cane-payment evidence"}
        )
        IntegrationConnection.objects.update_or_create(
            code="financier-api",
            defaults={"name":"Bank / SACCO integration","connection_type":"REST / webhook","status":"planned","enabled":False,"data_scope":"Offers, disbursement confirmation and settlement status"}
        )

        AuditEvent.objects.get_or_create(
            actor=mill_user,event_type="demo_obligation_acknowledged",object_type="Receivable",object_id=str(receivable.pk),
            defaults={"description":"Demo mill acknowledgement created for product demonstration."}
        )
        self.stdout.write(self.style.SUCCESS("Miwa360 demo ready: farmer / mill / sacco / oversight, password Demo123!"))
