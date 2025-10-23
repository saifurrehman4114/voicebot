from django.apps import AppConfig
import logging
import os
import sys

logger = logging.getLogger(__name__)


class VoiceApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'voice_api'

    def ready(self):
        """Initialize the appointment scheduler when Django starts"""
        # Skip if this is the autoreloader process
        # Only run in the actual worker process
        if 'runserver' in sys.argv:
            # Check if this is not the first autoreload cycle
            run_once = os.environ.get('SCHEDULER_STARTED')
            if run_once:
                return

            os.environ['SCHEDULER_STARTED'] = 'true'

        try:
            # Import here to avoid AppRegistryNotReady error
            from voice_api.scheduler import start_scheduler

            start_scheduler()
            logger.info("✓ Appointment scheduler started successfully")
        except Exception as e:
            logger.error(f"✗ Failed to start appointment scheduler: {str(e)}")
            import traceback
            traceback.print_exc()
