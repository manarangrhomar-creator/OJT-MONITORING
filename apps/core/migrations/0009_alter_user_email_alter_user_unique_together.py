from django.db import migrations, models


def deduplicate_names(apps, schema_editor):
    """Make existing full name combinations unique before adding the constraint."""
    from django.db.models import Count
    User = apps.get_model('core', 'User')

    dupes = (
        User.objects
        .values('first_name', 'last_name')
        .annotate(c=Count('id'))
        .filter(c__gt=1, first_name__gt='', last_name__gt='')
    )
    for d in dupes:
        users = list(
            User.objects.filter(
                first_name__iexact=d['first_name'],
                last_name__iexact=d['last_name']
            ).order_by('created_at')
        )
        # Keep the first one as-is, append a suffix to the rest
        for i, user in enumerate(users[1:], start=2):
            user.last_name = f"{user.last_name} ({i})"
            user.save(update_fields=['last_name'])


def deduplicate_emails(apps, schema_editor):
    """Make existing emails unique before adding the constraint."""
    from django.db.models import Count
    User = apps.get_model('core', 'User')

    dupes = (
        User.objects
        .values('email')
        .annotate(c=Count('id'))
        .filter(c__gt=1)
    )
    for d in dupes:
        users = list(
            User.objects.filter(email=d['email']).order_by('created_at')
        )
        for i, user in enumerate(users[1:], start=2):
            base, ext = user.email.rsplit('@', 1)
            user.email = f"{base}+dup{i}@{ext}"
            user.save(update_fields=['email'])
            # Also update username if it was set to the email
            if user.username == d['email'] or user.username == base:
                user.username = f"{base}+dup{i}"
                user.save(update_fields=['username'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_course_is_active_alter_notification_is_read_and_more'),
    ]

    operations = [
        migrations.RunPython(deduplicate_emails, migrations.RunPython.noop),
        migrations.RunPython(deduplicate_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(error_messages={'unique': 'A user with that email already exists.'}, max_length=254, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='user',
            unique_together={('first_name', 'last_name')},
        ),
    ]
