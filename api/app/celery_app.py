from celery import Celery
from app.config import settings

celery_app = Celery(
    "lt_oosaka",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.sample"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Tokyo",
    enable_utc=True,
)
