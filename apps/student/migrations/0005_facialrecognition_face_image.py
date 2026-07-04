# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0004_alter_studentprofile_course'),
    ]

    operations = [
        migrations.AddField(
            model_name='facialrecognition',
            name='face_image',
            field=models.BinaryField(blank=True, null=True),
        ),
    ]
