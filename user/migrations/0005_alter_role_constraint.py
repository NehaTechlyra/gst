# Generated migration to fix Role unique constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_add_permission_types_data'),
    ]

    operations = [
        # Remove the old unique_together constraint on role_name
        migrations.AlterField(
            model_name='role',
            name='role_name',
            field=models.CharField(max_length=150),
        ),
        # Add the new composite unique constraint
        migrations.AddConstraint(
            model_name='role',
            constraint=models.UniqueConstraint(
                fields=['role_name', 'company'],
                name='unique_role_per_company'
            ),
        ),
    ]
