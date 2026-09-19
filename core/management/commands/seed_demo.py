from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Profile, Farmer, Farm, Mill, Delivery, Receivable, AuditEvent

class Command(BaseCommand):
    help = "Create CanePay demo accounts and one sample receivable"

    def handle(self, *args, **kwargs):
        password = "Demo123!"
        farmer_user, _ = User.objects.get_or_create(username="farmer", defaults={"first_name":"Jane","last_name":"Atieno","email":"farmer@example.com"})
        mill_user, _ = User.objects.get_or_create(username="mill", defaults={"first_name":"Mill","last_name":"Officer"})
        sacco_user, _ = User.objects.get_or_create(username="sacco", defaults={"first_name":"Finance","last_name":"Officer"})
        ksb_user, _ = User.objects.get_or_create(username="ksb", defaults={"first_name":"KSB","last_name":"Analyst"})
        for u in [farmer_user,mill_user,sacco_user,ksb_user]:
            u.set_password(password); u.save()
        Profile.objects.update_or_create(user=farmer_user, defaults={"role":"farmer","organisation":"","phone":"0712345678"})
        Profile.objects.update_or_create(user=mill_user, defaults={"role":"mill","organisation":"Muhoroni Sugar Mill"})
        Profile.objects.update_or_create(user=sacco_user, defaults={"role":"financier","organisation":"Farmers Growth SACCO"})
        Profile.objects.update_or_create(user=ksb_user, defaults={"role":"regulator","organisation":"Kenya Sugar Board"})
        farmer, _ = Farmer.objects.update_or_create(user=farmer_user, defaults={"national_id":"ID-DEMO-001","farmer_number":"FRM-2026-001","county":"Kisumu","verified":True})
        mill, _ = Mill.objects.update_or_create(code="MSM", defaults={"name":"Muhoroni Sugar Mill","county":"Kisumu","verified":True,"payment_risk":"medium"})
        farm, _ = Farm.objects.update_or_create(farm_code="FARM-MUH-001", defaults={"farmer":farmer,"acreage":Decimal("3.20"),"location":"Muhoroni, Kisumu","variety":"CO 421"})
        delivery, _ = Delivery.objects.update_or_create(reference="DLV-2026-0001", defaults={
            "farmer":farmer,"farm":farm,"mill":mill,"delivered_at":timezone.now()-timedelta(hours=2),
            "gross_weight_tonnes":Decimal("18.40"),"accepted_weight_tonnes":Decimal("18.00"),
            "quality_score":Decimal("15.10"),"price_per_tonne":Decimal("5750.00"),"deductions":Decimal("4500.00"),
            "status":"acknowledged","verified_by":mill_user,"verified_at":timezone.now()-timedelta(hours=1,minutes=30),
        })
        receivable, _ = Receivable.objects.update_or_create(delivery=delivery, defaults={
            "reference":"CP-000001","amount":delivery.amount_payable,"due_date":timezone.localdate()+timedelta(days=14),
            "mill_acknowledged":True,"acknowledged_by":mill_user,"acknowledged_at":timezone.now()-timedelta(hours=1),"status":"verified"
        })
        AuditEvent.objects.get_or_create(actor=mill_user,event_type="receivable_acknowledged",object_type="Receivable",object_id=str(receivable.pk),defaults={"description":f"Mill acknowledged obligation of KES {receivable.amount:,.2f}."})
        self.stdout.write(self.style.SUCCESS("Demo data ready. Login with farmer/mill/sacco/ksb and password Demo123!"))
