from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Bot', '0018_order_courier_contact_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='icon',
            field=models.ImageField(blank=True, null=True, upload_to='service_icons/', verbose_name='Ikonka'),
        ),
    ]
