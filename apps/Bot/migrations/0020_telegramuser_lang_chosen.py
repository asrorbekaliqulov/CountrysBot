from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Bot', '0019_service_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramuser',
            name='lang_chosen',
            field=models.BooleanField(default=False, verbose_name='Til tanlangan'),
        ),
        migrations.RunPython(
            lambda apps, schema_editor: apps.get_model('Bot', 'TelegramUser').objects.update(lang_chosen=True),
            migrations.RunPython.noop,
        ),
    ]
