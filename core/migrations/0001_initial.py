from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Farmer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("national_id", models.CharField(max_length=40, unique=True)),
                ("farmer_number", models.CharField(max_length=40, unique=True)),
                ("county", models.CharField(blank=True, max_length=80)),
                ("verified", models.BooleanField(default=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Mill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, unique=True)),
                ("code", models.CharField(max_length=20, unique=True)),
                ("county", models.CharField(blank=True, max_length=80)),
                ("verified", models.BooleanField(default=True)),
                ("payment_risk", models.CharField(choices=[("low","Low"),("medium","Medium"),("high","High")], default="medium", max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("farmer","Farmer"),("mill","Mill"),("financier","Bank / SACCO"),("regulator","Regulator / Administrator")], max_length=20)),
                ("organisation", models.CharField(blank=True, max_length=160)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Farm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("farm_code", models.CharField(max_length=40, unique=True)),
                ("acreage", models.DecimalField(decimal_places=2, max_digits=8)),
                ("location", models.CharField(max_length=160)),
                ("variety", models.CharField(blank=True, max_length=80)),
                ("farmer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="farms", to="core.farmer")),
            ],
        ),
        migrations.CreateModel(
            name="Delivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=40, unique=True)),
                ("delivered_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("gross_weight_tonnes", models.DecimalField(decimal_places=2, max_digits=10)),
                ("accepted_weight_tonnes", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quality_score", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("price_per_tonne", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deductions", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("pending","Pending verification"),("verified","Verified"),("acknowledged","Mill acknowledged"),("settled","Settled")], default="pending", max_length=20)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deliveries", to="core.farm")),
                ("farmer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deliveries", to="core.farmer")),
                ("mill", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="deliveries", to="core.mill")),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_deliveries", to=settings.AUTH_USER_MODEL)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Receivable",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=40, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("due_date", models.DateField()),
                ("mill_acknowledged", models.BooleanField(default=False)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("draft","Draft"),("verified","Verified / available"),("finance_requested","Finance requested"),("financed","Financed"),("settled","Settled"),("cancelled","Cancelled")], default="draft", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("acknowledged_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acknowledged_receivables", to=settings.AUTH_USER_MODEL)),
                ("delivery", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="receivable", to="core.delivery")),
            ],
        ),
        migrations.CreateModel(
            name="FinanceRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("consent_to_share", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("open","Open"),("accepted","Accepted"),("closed","Closed")], default="open", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("farmer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.farmer")),
                ("receivable", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="finance_request", to="core.receivable")),
            ],
        ),
        migrations.CreateModel(
            name="FinanceOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("advance_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("finance_cost", models.DecimalField(decimal_places=2, max_digits=12)),
                ("settlement_amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(choices=[("offered","Offered"),("accepted","Accepted"),("declined","Declined"),("disbursed","Disbursed")], default="offered", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("disbursed_at", models.DateTimeField(blank=True, null=True)),
                ("financier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="finance_offers", to=settings.AUTH_USER_MODEL)),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offers", to="core.financerequest")),
            ],
        ),
        migrations.CreateModel(
            name="ReceivableAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("active", models.BooleanField(default=True)),
                ("assigned_to", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assigned_receivables", to=settings.AUTH_USER_MODEL)),
                ("offer", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to="core.financeoffer")),
                ("receivable", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="assignment", to="core.receivable")),
            ],
        ),
        migrations.CreateModel(
            name="Settlement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount_received", models.DecimalField(decimal_places=2, max_digits=12)),
                ("settled_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("reference", models.CharField(blank=True, max_length=80)),
                ("financier", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("receivable", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="settlement", to="core.receivable")),
            ],
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=80)),
                ("object_type", models.CharField(max_length=80)),
                ("object_id", models.CharField(max_length=80)),
                ("description", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["-created_at"]},
        ),
    ]
