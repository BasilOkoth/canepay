from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Profile(models.Model):
    ROLE_CHOICES = [
        ("farmer", "Farmer"),
        ("mill", "Miller"),
        ("financier", "Bank / SACCO"),
        ("regulator", "Oversight"),
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
    ksb_grower_id = models.CharField(max_length=80, blank=True, db_index=True)
    county = models.CharField(max_length=80, blank=True)
    verified = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} – {self.farmer_number}"

class Mill(models.Model):
    name = models.CharField(max_length=160, unique=True)
    code = models.CharField(max_length=20, unique=True)
    external_id = models.CharField(max_length=80, blank=True, db_index=True)
    county = models.CharField(max_length=80, blank=True)
    verified = models.BooleanField(default=True)
    payment_terms_days = models.PositiveIntegerField(default=30)
    payment_risk = models.CharField(
        max_length=20,
        choices=[("low","Low"),("medium","Medium"),("high","High")],
        default="medium",
    )
    def __str__(self):
        return self.name

class Farm(models.Model):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name="farms")
    farm_code = models.CharField(max_length=40, unique=True)
    external_id = models.CharField(max_length=80, blank=True, db_index=True)
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
    SOURCE_CHOICES = [
        ("manual", "Manual entry"),
        ("mill_api", "Mill system / API"),
        ("simis", "Industry information system"),
        ("qbcps", "Quality / cane payment system"),
        ("other", "Other integrated source"),
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
    source_system = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="manual")
    external_reference = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    delivery_ticket_number = models.CharField(max_length=80, blank=True)
    mill_approved = models.BooleanField(default=False)
    imported_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="verified_deliveries")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_system", "external_reference"],
                name="unique_delivery_external_reference",
            )
        ]

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
        ("draft", "Awaiting mill acknowledgement"),
        ("verified", "Available for financing"),
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
    def farmer(self): return self.delivery.farmer
    @property
    def mill(self): return self.delivery.mill
    @property
    def is_finance_locked(self):
        return hasattr(self, "assignment") and self.assignment.active
    def __str__(self): return self.reference

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
    amount_to_financier = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_to_farmer = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_destination = models.CharField(max_length=180, blank=True)
    notes = models.TextField(blank=True)
    settled_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=80, blank=True)

class IntegrationConnection(models.Model):
    STATUS_CHOICES = [("planned","Planned"),("sandbox","Sandbox"),("connected","Connected"),("error","Attention needed")]
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=160)
    connection_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    enabled = models.BooleanField(default=False)
    data_scope = models.CharField(max_length=220, blank=True)
    base_url = models.URLField(blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.name

class IntegrationEvent(models.Model):
    DIRECTION_CHOICES = [("inbound","Inbound"),("outbound","Outbound")]
    STATUS_CHOICES = [("success","Success"),("rejected","Rejected"),("error","Error")]
    connection = models.ForeignKey(IntegrationConnection, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    event_type = models.CharField(max_length=80)
    external_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]

class AuditEvent(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]
