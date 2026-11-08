import logging
import signal
import time

from app.core.config import ensure_authentication_ready, ensure_deployment_ready, settings
from app.services.processing_queue import process_one_job, worker_identifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('recall_atlas.worker')
_stop_requested = False


def _request_stop(signum, frame) -> None:
    global _stop_requested
    _stop_requested = True


def main() -> None:
    ensure_authentication_ready(
        settings.app_env,
        settings.secret_key,
        settings.admin_email,
        settings.admin_initial_password,
    )
    ensure_deployment_ready(
        settings.app_env,
        settings.database_url,
        settings.storage_backend,
        settings.object_storage_bucket,
    )
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
    worker_id = worker_identifier()
    logger.info('Processing worker started: %s', worker_id)
    while not _stop_requested:
        try:
            worked = process_one_job(worker_id)
        except Exception:
            logger.exception('Processing worker loop failed; retrying after poll interval')
            worked = False
        if not worked:
            time.sleep(settings.processing_worker_poll_seconds)
    logger.info('Processing worker stopped: %s', worker_id)


if __name__ == '__main__':
    main()
