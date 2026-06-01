import os
import sys
import logging
import threading
from django.apps import AppConfig

logger = logging.getLogger(__name__)


def _start_scheduler():
    try:
        from Lyraerp.scheduler import start
        start()
        logger.info("[OK] [STARTUP] APScheduler started successfully")
    except Exception as e:
        logger.error(f"[ERROR] [STARTUP] Scheduler failed to start: {e}", exc_info=True)


class LyraerpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Lyraerp'

    def ready(self):
        if 'manage.py' in sys.argv and any(
            cmd in sys.argv for cmd in [
                'makemigrations', 'migrate', 'createsuperuser', 'shell',
                'collectstatic', 'check', 'showmigrations', 'sqlmigrate',
            ]
        ):
            logger.info("[SCHEDULER] Skipping scheduler start for management command")
            return

        # In development, Django spawns two processes.
        # RUN_MAIN=true is set only in the reloader child (the one that stays alive).
        # In production (gunicorn), RUN_MAIN is not set but there is no reloader,
        # so we start the scheduler in that case too.
        is_reloader_child = os.environ.get('RUN_MAIN') == 'true'
        is_production = not any('runserver' in arg for arg in sys.argv)

        if is_reloader_child or is_production:
            logger.info(f"[SCHEDULER] Starting scheduler (RUN_MAIN={os.environ.get('RUN_MAIN')}, production={is_production})")
            thread = threading.Thread(target=_start_scheduler, daemon=True)
            thread.start()
        else:
            logger.info("[SCHEDULER] Skipping scheduler - initial process, waiting for reloader child")
