from django.db import migrations


def drop_column_if_exists(apps, schema_editor):
    """Drop column if it exists"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='sales_salesquotation' AND COLUMN_NAME='created_from_crm'
        """)
        if cursor.fetchone():
            cursor.execute("ALTER TABLE `sales_salesquotation` DROP COLUMN `created_from_crm`")


def add_column_if_not_exists(apps, schema_editor):
    """Add column back if it doesn't exist"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME='sales_salesquotation' AND COLUMN_NAME='created_from_crm'
        """)
        if not cursor.fetchone():
            cursor.execute(
                "ALTER TABLE `sales_salesquotation` "
                "ADD COLUMN `created_from_crm` tinyint(1) NOT NULL DEFAULT 0"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0004_salesinvoiceitem_hsn_code_salesorderitem_hsn_code_and_more'),
    ]

    operations = [
        migrations.RunPython(drop_column_if_exists, add_column_if_not_exists),
    ]
