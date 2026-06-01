from django.db import migrations, models
import django.db.models.deletion


def _column_exists(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            LIMIT 1
            """,
            [table_name, column_name],
        )
        return cursor.fetchone() is not None


def _index_exists(schema_editor, table_name, index_name):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND INDEX_NAME = %s
            LIMIT 1
            """,
            [table_name, index_name],
        )
        return cursor.fetchone() is not None


def _fk_exists_for_column(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
            LIMIT 1
            """,
            [table_name, column_name],
        )
        return cursor.fetchone() is not None


def add_item_fk_columns_if_missing(apps, schema_editor):
    Item = apps.get_model('Items', 'Item')
    Category = apps.get_model('category', 'Category')
    TypeModel = apps.get_model('type', 'Type')

    item_table = Item._meta.db_table
    category_table = Category._meta.db_table
    type_table = TypeModel._meta.db_table
    qn = schema_editor.quote_name

    idx_category = 'idx_items_item_category_id'
    idx_item_type = 'idx_items_item_item_type_id'
    fk_category = 'fk_items_item_category_id'
    fk_item_type = 'fk_items_item_item_type_id'

    with schema_editor.connection.cursor() as cursor:
        if not _column_exists(schema_editor, item_table, 'category_id'):
            cursor.execute(
                f"ALTER TABLE {qn(item_table)} "
                f"ADD COLUMN {qn('category_id')} bigint NULL"
            )
        if not _index_exists(schema_editor, item_table, idx_category):
            cursor.execute(
                f"ALTER TABLE {qn(item_table)} "
                f"ADD INDEX {qn(idx_category)} ({qn('category_id')})"
            )
        if not _fk_exists_for_column(schema_editor, item_table, 'category_id'):
            cursor.execute(
                f"ALTER TABLE {qn(item_table)} "
                f"ADD CONSTRAINT {qn(fk_category)} "
                f"FOREIGN KEY ({qn('category_id')}) "
                f"REFERENCES {qn(category_table)} ({qn('id')}) "
                f"ON DELETE SET NULL"
            )

        if not _column_exists(schema_editor, item_table, 'item_type_id'):
            cursor.execute(
                f"ALTER TABLE {qn(item_table)} "
                f"ADD COLUMN {qn('item_type_id')} bigint NULL"
            )
        if not _index_exists(schema_editor, item_table, idx_item_type):
            cursor.execute(
                f"ALTER TABLE {qn(item_table)} "
                f"ADD INDEX {qn(idx_item_type)} ({qn('item_type_id')})"
            )
        if not _fk_exists_for_column(schema_editor, item_table, 'item_type_id'):
            cursor.execute(
                f"ALTER TABLE {qn(item_table)} "
                f"ADD CONSTRAINT {qn(fk_item_type)} "
                f"FOREIGN KEY ({qn('item_type_id')}) "
                f"REFERENCES {qn(type_table)} ({qn('id')}) "
                f"ON DELETE SET NULL"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0001_initial'),
        ('type', '0001_initial'),
        ('Items', '0003_auto_20251223_1527'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_item_fk_columns_if_missing,
                    reverse_code=migrations.RunPython.noop,
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name='item',
                    name='category',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='items',
                        to='category.category',
                        verbose_name='Category',
                    ),
                ),
                migrations.AddField(
                    model_name='item',
                    name='item_type',
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='items',
                        to='type.type',
                        verbose_name='Item Type',
                    ),
                ),
            ],
        ),
    ]
