from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Profile(models.Model):
    ROLE_CHOICES = [
        ("farmer", "Farmer"),
        ("mill", "Mill"),
        ("financier", "Bank / SACCO"),
        ("regulator", "Regulator / Administrator"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    organisation = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

class Farmer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    national_id = models.CharField(max_length=40, unique=True)
    farmer_number = models.CharField(max_length=40, unique=True)
    county = models.CharField(max_length=80, blank=True)
    verified = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} – {self.farmer_number}"

class Mill(models.Model):
    name = models.CharField(max_length=160, unique=True)
    code = models.CharField(max_length=20, unique=True)
    county = models.CharField(max_length=80, blank=True)
    verified = models.BooleanField(default=True)
    payment_risk = models.CharField(max_length=20, choices=[("low","Low"),("medium","Medium"),("high","High")], default="medium")

    def __str__(self):
        return self.name

class Farm(models.Model):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="farms")
    farm_code = models.CharField(max_length=40, unique=True)
    acreage = models.DecimalField(max_digits=8, decimal_places=2)
    location = models.CharField(max_length=160)
    variety = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return self.farm_code

class Delivery(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending verification"),
        ("verified", "Verified"),
        ("acknowledged", "Mill acknowledged"),
        ("settled", "Settled"),
    ]
    reference = models.CharField(max_length=40, unique=True)
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name="deliveries")
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name="deliveries")
    mill = models.ForeignKey(Mill, on_delete=models.PROTECT, related_name="deliveries")
    delivered_at = models.DateTimeField(default=timezone.now)
    gross_weight_tonnes = models.DecimalField(max_digits=10, decimal_places=2)
    accepted_weight_tonnes = models.DecimalField(max_digits=10, decimal_places=2)
    quality_score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    price_per_tonne = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_deliveries")
    verified_at = models.DateTimeField(null=True, blank=True)

    @property
    def gross_value(self):
        return (self.accepted_weight_tonnes or Decimal("0")) * (self.price_per_tonne or Decimal("0"))

    @property
    def amount_payable(self):
        return max(Decimal("0"), self.gross_value - (self.deductions or Decimal("0")))

    def __str__(self):
        return self.reference

class Receivable(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("verified", "Verified / available"),
        ("finance_requested", "Finance requested"),
        ("financed", "Financed"),
        ("settled", "Settled"),
        ("cancelled", "Cancelled"),
    ]
    reference = models.CharField(max_length=40, unique=True)
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name="receivable")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    mill_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="acknowledged_receivables")
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def farmer(self):
        return self.delivery.farmer

    @property
    def mill(self):
        return self.delivery.mill

    def __str__(self):
        return self.reference

class FinanceRequest(models.Model):
    receivable = models.OneToOneField(Receivable, on_delete=models.CASCADE, related_name="finance_request")
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT)
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    consent_to_share = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[("open","Open"),("accepted","Accepted"),("closed","Closed")], default="open")
    created_at = models.DateTimeField(auto_now_add=True)

class FinanceOffer(models.Model):
    request = models.ForeignKey(FinanceRequest, on_delete=models.CASCADE, related_name="offers")
    financier = models.ForeignKey(User, on_delete=models.PROTECT, related_name="finance_offers")
    advance_amount = models.DecimalField(max_digits=12, decimal_places=2)
    finance_cost = models.DecimalField(max_digits=12, decimal_places=2)
    settlement_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("offered","Offered"),("accepted","Accepted"),("declined","Declined"),("disbursed","Disbursed")], default="offered")
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)

class ReceivableAssignment(models.Model):
    receivable = models.OneToOneField(Receivable, on_delete=models.CASCADE, related_name="assignment")
    offer = models.OneToOneField(FinanceOffer, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, related_name="assigned_receivables")
    assigned_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

class Settlement(models.Model):
    receivable = models.OneToOneField(Receivable, on_delete=models.PROTECT, related_name="settlement")
    financier = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    amount_received = models.DecimalField(max_digits=12, decimal_places=2)
    settled_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=80, blank=True)

class AuditEvent(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
