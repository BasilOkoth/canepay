from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_miwa360_upgrade"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="account_status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("pending", "Pending verification"),
                    ("suspended", "Suspended"),
                ],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
    ]
