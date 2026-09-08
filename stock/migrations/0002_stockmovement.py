import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stock', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('adjustment_in', 'Adjustment In'), ('adjustment_out', 'Adjustment Out'), ('transfer_in', 'Transfer In'), ('transfer_out', 'Transfer Out')], max_length=20)),
                ('quantity', models.DecimalField(decimal_places=2, help_text='Always a positive magnitude; direction is given by movement_type', max_digits=12)),
                ('reference_type', models.CharField(choices=[('manual_adjustment', 'Manual Adjustment'), ('warehouse_transfer', 'Warehouse Transfer')], max_length=30)),
                ('reference_id', models.PositiveIntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, help_text='User who recorded this movement', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_movements_created', to=settings.AUTH_USER_MODEL)),
                ('linked_movement', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='paired_with', to='stock.stockmovement')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_movements', to='stock.stock')),
            ],
            options={
                'verbose_name': 'Stock Movement',
                'verbose_name_plural': 'Stock Movements',
                'ordering': ['-created_at'],
            },
        ),
    ]
