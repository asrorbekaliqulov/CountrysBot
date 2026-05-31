import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Bot", "0017_alter_order_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="contact_phone",
            field=models.CharField(
                blank=True,
                max_length=20,
                null=True,
                verbose_name="Aloqa telefoni",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="courier",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_orders",
                to="Bot.telegramuser",
                verbose_name="Kuryer",
            ),
        ),
    ]
