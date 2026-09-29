from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_profile_account_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExternalIdentity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_type", models.CharField(choices=[("farmer", "Farmer"), ("farm", "Farm"), ("mill", "Mill")], db_index=True, max_length=20)),
                ("source_system", models.CharField(db_index=True, max_length=60)),
                ("identifier_type", models.CharField(blank=True, max_length=60)),
                ("external_identifier", models.CharField(db_index=True, max_length=120)),
                ("verified", models.BooleanField(default=False)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("farm", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="external_identities", to="core.farm")),
                ("farmer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="external_identities", to="core.farmer")),
                ("mill", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="external_identities", to="core.mill")),
            ],
        ),
        migrations.AddConstraint(
            model_name="externalidentity",
            constraint=models.UniqueConstraint(fields=("source_system", "entity_type", "external_identifier"), name="unique_external_identity"),
        ),
        migrations.CreateModel(
            name="CaneQualityTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_system", models.CharField(db_index=True, default="qbcps", max_length=60)),
                ("external_reference", models.CharField(blank=True, db_index=True, max_length=120, null=True)),
                ("pol_percent", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ("brix_percent", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ("fibre_percent", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ("moisture_percent", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ("extraneous_matter_percent", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ("tested_at", models.DateTimeField(blank=True, null=True)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("delivery", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="quality_test", to="core.delivery")),
            ],
        ),
        migrations.AddConstraint(
            model_name="canequalitytest",
            constraint=models.UniqueConstraint(fields=("source_system", "external_reference"), name="unique_quality_external_reference"),
        ),
        migrations.CreateModel(
            name="PricingAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_system", models.CharField(default="manual", max_length=60)),
                ("pricing_reference", models.CharField(blank=True, db_index=True, max_length=120)),
                ("pricing_period", models.CharField(blank=True, max_length=40)),
                ("calculated_price_per_tonne", models.DecimalField(decimal_places=2, max_digits=12)),
                ("expected_gross_value", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("expected_deductions", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("expected_net_value", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("mill_declared_net_value", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("status", models.CharField(choices=[("estimated", "Estimated"), ("verified", "Verified"), ("reconciled", "Reconciled"), ("variance", "Variance detected")], default="estimated", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("assessed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("delivery", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="pricing_assessment", to="core.delivery")),
            ],
        ),
        migrations.CreateModel(
            name="FarmExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("expense_date", models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ("category", models.CharField(choices=[("land_preparation", "Land preparation"), ("seed_cane", "Seed cane / planting material"), ("fertiliser", "Fertiliser"), ("chemicals", "Herbicides / crop protection"), ("labour", "Labour"), ("harvesting", "Harvesting"), ("transport", "Transport"), ("irrigation", "Irrigation / water"), ("machinery", "Machinery / equipment"), ("finance", "Finance / interest cost"), ("other", "Other")], max_length=30)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("description", models.CharField(blank=True, max_length=220)),
                ("supplier", models.CharField(blank=True, max_length=160)),
                ("external_reference", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="core.farm")),
                ("farmer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="core.farmer")),
            ],
            options={"ordering": ["-expense_date", "-id"]},
        ),
    ]
