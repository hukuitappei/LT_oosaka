from app.celery_app import celery_app


@celery_app.task
def add(x: int, y: int) -> int:
    return x + y


@celery_app.task
def ping() -> str:
    return "pong"
