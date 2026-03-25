import os
from celery import Celery
from celery.schedules import crontab

# Configure Celery
# We use Redis as both the message broker and the result backend.
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "quant_platform",
    broker=redis_url,
    backend=redis_url,
    include=["app.core.tasks"]
)

# Optional: Configure routing or limits
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,
)

# Configure Celery Beat for daily execution
celery_app.conf.beat_schedule = {
    "run-daily-quantitative-pipeline": {
        "task": "app.core.tasks.run_daily_pipeline",
        # Run daily at 6:00 AM EST
        "schedule": crontab(hour=6, minute=0),
    },
}
