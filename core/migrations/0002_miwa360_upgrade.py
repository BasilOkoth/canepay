from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("core","0001_initial")]
    operations = [
        migrations.AlterField(
            model_name="profile", name="role",
            field=models.CharField(choices=[("farmer","Farmer"),("mill","Miller"),("financier","Bank / SACCO"),("regulator","Oversight")], max_length=20),
        ),
        migrations.AddField(model_name="farmer", name="ksb_grower_id", field=models.CharField(blank=True, db_index=True, max_length=80)),
        migrations.AddField(model_name="mill", name="external_id", field=models.CharField(blank=True, db_index=True, max_length=80)),
        migrations.AddField(model_name="mill", name="payment_terms_days", field=models.PositiveIntegerField(default=30)),
        migrations.AddField(model_name="farm", name="external_id", field=models.CharField(blank=True, db_index=True, max_length=80)),
        migrations.AddField(model_name="delivery", name="source_system", field=models.CharField(choices=[("manual","Manual entry"),("mill_api","Mill system / API"),("simis","Industry information system"),("qbcps","Quality / cane payment system"),("other","Other integrated source")], default="manual", max_length=30)),
        migrations.AddField(model_name="delivery", name="external_reference", field=models.CharField(blank=True, db_index=True, max_length=100, null=True)),
        migrations.AddField(model_name="delivery", name="delivery_ticket_number", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="delivery", name="mill_approved", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="delivery", name="imported_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddConstraint(model_name="delivery", constraint=models.UniqueConstraint(fields=("source_system","external_reference"), name="unique_delivery_external_reference")),
        migrations.AlterField(model_name="receivable", name="status", field=models.CharField(choices=[("draft","Awaiting mill acknowledgement"),("verified","Available for financing"),("finance_requested","Finance requested"),("financed","Financed"),("settled","Settled"),("cancelled","Cancelled")], default="draft", max_length=30)),
        migrations.AddField(model_name="settlement", name="amount_to_financier", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="settlement", name="amount_to_farmer", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="settlement", name="payment_destination", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="settlement", name="notes", field=models.TextField(blank=True)),
        migrations.CreateModel(
            name="IntegrationConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("connection_type", models.CharField(max_length=80)),
                ("status", models.CharField(choices=[("planned","Planned"),("sandbox","Sandbox"),("connected","Connected"),("error","Attention needed")], default="planned", max_length=20)),
                ("enabled", models.BooleanField(default=False)),
                ("data_scope", models.CharField(blank=True, max_length=220)),
                ("base_url", models.URLField(blank=True)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="IntegrationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("direction", models.CharField(choices=[("inbound","Inbound"),("outbound","Outbound")], max_length=20)),
                ("event_type", models.CharField(max_length=80)),
                ("external_reference", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("success","Success"),("rejected","Rejected"),("error","Error")], max_length=20)),
                ("detail", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("connection", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="core.integrationconnection")),
            ],
            options={"ordering":["-created_at"]},
        ),
    ]
