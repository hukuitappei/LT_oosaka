from celery import Celery
from celery.schedules import crontab
from app.config import settings

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
    beat_schedule={
        "generate-weekly-digests": {
            "task": "app.tasks.extract.generate_scheduled_weekly_digests_task",
            "schedule": crontab(minute=0, hour=9, day_of_week="mon"),
        }
    },
)
