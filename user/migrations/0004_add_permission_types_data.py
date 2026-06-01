# Generated migration for adding permission types data
# Created: January 27, 2026

from django.db import migrations


def add_permission_types_data(apps, schema_editor):
    """Add all permission types to the database"""
    PermissionType = apps.get_model('user', 'PermissionType')

    permission_types = [
        {'id': 3, 'name': 'Create'},
        {'id': 5, 'name': 'Delete'},
        {'id': 4, 'name': 'Edit'},
        {'id': 1, 'name': 'Full Access'},
        {'id': 2, 'name': 'View'},
    ]

    for perm_type in permission_types:
        PermissionType.objects.update_or_create(
            id=perm_type['id'],
            defaults={'name': perm_type['name']}
        )


def remove_permission_types_data(apps, schema_editor):
    """Remove all added permission types (reverse migration)"""
    PermissionType = apps.get_model('user', 'PermissionType')
    
    perm_type_ids = [1, 2, 3, 4, 5]
    
    PermissionType.objects.filter(id__in=perm_type_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_add_modules_data'),
    ]

    operations = [
        migrations.RunPython(
            add_permission_types_data,
            reverse_code=remove_permission_types_data
        ),
    ]
