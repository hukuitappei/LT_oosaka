def test_celery_routes_tasks_to_dedicated_queues():
    from app.celery_app import celery_app

    routes = celery_app.conf.task_routes

    assert routes["app.tasks.extract.extract_pr_task"]["queue"] == "webhook_ingest"
    assert routes["app.tasks.extract.extract_learning_items_task"]["queue"] == "learning_extract"
    assert routes["app.tasks.extract.reanalyze_pr_task"]["queue"] == "learning_extract"
    assert routes["app.tasks.extract.generate_digest_task"]["queue"] == "digest_generate"
    assert routes["app.tasks.extract.generate_scheduled_weekly_digests_task"]["queue"] == "digest_generate"
    assert routes["app.tasks.extract.cleanup_retention_task"]["queue"] == "retention_cleanup"


def test_celery_declares_all_named_queues():
    from app.celery_app import celery_app

    queue_names = {queue.name for queue in celery_app.conf.task_queues}

    assert queue_names == {
        "webhook_ingest",
        "learning_extract",
        "digest_generate",
        "retention_cleanup",
    }
