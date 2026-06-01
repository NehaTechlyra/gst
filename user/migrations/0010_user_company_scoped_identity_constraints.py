from django.db import migrations, models


def _get_index_columns(cursor, index_name):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = 'user_user'
          AND index_name = %s
        ORDER BY seq_in_index
        """,
        [index_name],
    )
    return [row[0] for row in cursor.fetchall()]


def _value_exists(cursor, field_name, company_id, value, exclude_id):
    cursor.execute(
        f"""
        SELECT 1
        FROM user_user
        WHERE company_id = %s
          AND LOWER({field_name}) = LOWER(%s)
          AND id <> %s
        LIMIT 1
        """,
        [company_id, value, exclude_id],
    )
    return cursor.fetchone() is not None


def _fit_length(value, max_len=45):
    if value is None:
        return ""
    return value[:max_len]


def _build_unique_username(cursor, company_id, original, user_id):
    base = (original or "user").strip() or "user"
    candidate = _fit_length(base)
    if not _value_exists(cursor, "usr_name", company_id, candidate, user_id):
        return candidate

    suffix = f"_{user_id}"
    base_cut = _fit_length(base, 45 - len(suffix))
    candidate = f"{base_cut}{suffix}"
    while _value_exists(cursor, "usr_name", company_id, candidate, user_id):
        suffix = f"_{user_id}x"
        base_cut = _fit_length(base, 45 - len(suffix))
        candidate = f"{base_cut}{suffix}"
    return candidate


def _build_unique_email(cursor, company_id, original, user_id):
    raw = (original or "").strip()
    if "@" in raw:
        local, domain = raw.split("@", 1)
        local = local or "user"
        suffix = f"+dup{user_id}"
        local_cut = _fit_length(local, max_len=max(1, 45 - len(domain) - 1 - len(suffix)))
        candidate = f"{local_cut}{suffix}@{domain}"
    else:
        base = raw or "user"
        suffix = f"_dup{user_id}"
        base_cut = _fit_length(base, 45 - len(suffix))
        candidate = f"{base_cut}{suffix}"

    candidate = _fit_length(candidate)
    while _value_exists(cursor, "usr_mail", company_id, candidate, user_id):
        candidate = _fit_length(f"{candidate[:35]}_{user_id}")
    return candidate


def _resolve_duplicates(cursor, field_name, value_builder):
    cursor.execute(
        f"""
        SELECT company_id, LOWER({field_name}) AS key_val, COUNT(*) AS cnt
        FROM user_user
        WHERE company_id IS NOT NULL
          AND {field_name} IS NOT NULL
          AND {field_name} <> ''
        GROUP BY company_id, LOWER({field_name})
        HAVING COUNT(*) > 1
        """
    )
    duplicate_groups = cursor.fetchall()
    for company_id, key_val, _ in duplicate_groups:
        cursor.execute(
            f"""
            SELECT id, {field_name}
            FROM user_user
            WHERE company_id = %s
              AND LOWER({field_name}) = %s
            ORDER BY id
            """,
            [company_id, key_val],
        )
        rows = cursor.fetchall()
        # Keep oldest row unchanged, rewrite the rest.
        for row_id, old_value in rows[1:]:
            new_value = value_builder(cursor, company_id, old_value, row_id)
            cursor.execute(
                f"UPDATE user_user SET {field_name} = %s WHERE id = %s",
                [new_value, row_id],
            )


def normalize_company_scoped_user_identity(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        _resolve_duplicates(cursor, "usr_name", _build_unique_username)
        _resolve_duplicates(cursor, "usr_mail", _build_unique_email)


def ensure_company_scoped_user_constraints(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        targets = [
            ("unique_username_per_company", ["usr_name", "company_id"]),
            ("unique_email_per_company", ["usr_mail", "company_id"]),
        ]
        for index_name, expected_cols in targets:
            existing_cols = _get_index_columns(cursor, index_name)
            if not existing_cols:
                cols_sql = ", ".join(expected_cols)
                schema_editor.execute(
                    f"ALTER TABLE user_user ADD CONSTRAINT {index_name} UNIQUE ({cols_sql})"
                )
                continue
            if existing_cols != expected_cols:
                raise RuntimeError(
                    f"Index '{index_name}' exists on columns {existing_cols}, "
                    f"expected {expected_cols}. Please fix DB index manually."
                )


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0009_user_company_user_is_admin'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    normalize_company_scoped_user_identity,
                    reverse_code=migrations.RunPython.noop,
                ),
                migrations.RunPython(
                    ensure_company_scoped_user_constraints,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name='user',
                    constraint=models.UniqueConstraint(
                        fields=('usr_name', 'company'),
                        name='unique_username_per_company',
                    ),
                ),
                migrations.AddConstraint(
                    model_name='user',
                    constraint=models.UniqueConstraint(
                        fields=('usr_mail', 'company'),
                        name='unique_email_per_company',
                    ),
                ),
            ],
        ),
    ]
