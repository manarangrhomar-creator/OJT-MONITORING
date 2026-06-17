from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_user_approval_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='course',
            field=models.CharField(blank=True, help_text='Course/Program the coordinator oversees', max_length=255, null=True),
        ),
    ]
