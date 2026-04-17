import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure
from kombu import Queue

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "lt_oosaka",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.extract"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="learning_extract",
    task_queues=(
        Queue("webhook_ingest"),
        Queue("learning_extract"),
        Queue("digest_generate"),
        Queue("retention_cleanup"),
    ),
    task_routes={
        "app.tasks.extract.extract_pr_task": {"queue": "webhook_ingest"},
        "app.tasks.extract.extract_learning_items_task": {"queue": "learning_extract"},
        "app.tasks.extract.reanalyze_pr_task": {"queue": "learning_extract"},
        "app.tasks.extract.generate_digest_task": {"queue": "digest_generate"},
        "app.tasks.extract.generate_scheduled_weekly_digests_task": {"queue": "digest_generate"},
        "app.tasks.extract.cleanup_retention_task": {"queue": "retention_cleanup"},
    },
    beat_schedule={
        "generate-weekly-digests": {
            "task": "app.tasks.extract.generate_scheduled_weekly_digests_task",
            "schedule": crontab(minute=0, hour=9, day_of_week="mon"),
        },
        "cleanup-retention-data": {
            "task": "app.tasks.extract.cleanup_retention_task",
            "schedule": crontab(minute=30, hour=3),
        },
    },
)


@task_failure.connect
def on_task_permanent_failure(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    einfo=None,
    **kw,
):
    logger.error(
        "task_permanently_failed task=%s task_id=%s exc_type=%s exc=%s",
        getattr(sender, "name", str(sender)),
        task_id,
        type(exception).__name__,
        str(exception),
        stack_info=False,
    )
