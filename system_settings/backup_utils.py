import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.utils import timezone


# def _get_system_backup_root():
#     # Priority:
#     # 1) Explicit environment variable
#     # 2) Django setting override
#     # 3) OS-level user documents/home folder (outside project)
#     env_root = os.getenv('LYRA_BACKUP_DIR')
#     if env_root:
#         return Path(env_root)

#     settings_root = getattr(settings, 'BACKUP_STORAGE_DIR', None)
#     if settings_root:
#         return Path(settings_root)

#     documents_dir = Path.home() / 'Documents'
#     if documents_dir.exists():
#         return documents_dir / 'LyraERP_Backups'

#     return Path.home() / 'LyraERP_Backups'

def _get_system_backup_root():
    # Priority:
    # 1) Explicit environment variable
    # 2) Django setting override
    # 3) Project-local backup directory
    env_root = os.getenv('LYRA_BACKUP_DIR')
    if env_root:
        return Path(env_root)

    settings_root = getattr(settings, 'BACKUP_STORAGE_DIR', None)
    if settings_root:
        return Path(settings_root)

    return Path(settings.BASE_DIR) / 'backups'


def get_backup_storage_path(company_code=None):
    code = company_code or 'default'
    return _get_system_backup_root() / str(code)


def create_database_backup(db_alias='default', company_code=None):
    db_settings = connections[db_alias].settings_dict
    engine = (db_settings.get('ENGINE') or '').lower()

    code = company_code or db_alias
    backup_dir = get_backup_storage_path(code)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

    if 'mysql' in engine:
        db_name = db_settings.get('NAME')
        db_user = db_settings.get('USER')
        db_password = db_settings.get('PASSWORD') or ''
        db_host = db_settings.get('HOST') or 'localhost'
        db_port = str(db_settings.get('PORT') or '3306')

        backup_file = backup_dir / f"{db_name}_{timestamp}.sql"
        cmd = [
            'mysqldump',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--events',
            '-h', db_host,
            '-P', db_port,
            '-u', db_user,
            db_name,
        ]
        env = os.environ.copy()
        if db_password:
            env['MYSQL_PWD'] = db_password

        with backup_file.open('w', encoding='utf-8') as out_file:
            result = subprocess.run(
                cmd,
                stdout=out_file,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )

        if result.returncode != 0:
            backup_file.unlink(missing_ok=True)
            raise RuntimeError(result.stderr.strip() or 'mysqldump failed')

        return backup_file

    if 'sqlite3' in engine:
        src = Path(db_settings.get('NAME'))
        backup_file = backup_dir / f"{src.stem}_{timestamp}.sqlite3"
        shutil.copy2(src, backup_file)
        return backup_file

    raise RuntimeError(f"Backup is not supported for engine: {db_settings.get('ENGINE')}")
