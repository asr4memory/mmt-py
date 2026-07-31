from django.db import migrations
from django.db.models import OuterRef, Subquery


def backfill_created_at(apps, schema_editor):
    """Set created_at of existing profiles to the date the user joined.

    The preceding migration populates created_at with the migration timestamp,
    which is not the time the profile was created. A profile is created with
    its user (or on first access through User.safe_profile), so date_joined is
    the closest true value available.
    """
    Profile = apps.get_model('my_account', 'Profile')
    User = apps.get_model('my_account', 'User')

    date_joined = User.objects.filter(pk=OuterRef('user_id')).values('date_joined')[:1]
    Profile.objects.update(created_at=Subquery(date_joined))


class Migration(migrations.Migration):
    dependencies = [
        (
            'my_account',
            '0017_profile_created_at_profile_updated_at_tag_created_at_and_more',
        ),
    ]

    operations = [
        migrations.RunPython(backfill_created_at, migrations.RunPython.noop),
    ]
