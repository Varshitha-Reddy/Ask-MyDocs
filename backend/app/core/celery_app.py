"""
Celery application — production-grade background task queue.

Why Celery over FastAPI BackgroundTasks?
- BackgroundTasks: lives in RAM only. Server crashes → task lost forever.
- Celery + Redis: task is saved to Redis before running. Server crashes →
  worker restarts and picks the task up again. Nothing is lost.

Redis is used as both:
  broker  — where tasks are sent to (the queue)
  backend — where task results/status are stored
"""
from celery import Celery

from app.config import settings

# Create Celery app — point both broker and result backend at Redis
celery_app = Celery(
    "rag_worker",
    broker=settings.redis_url,       # tasks go into this queue
    backend=settings.redis_url,      # task results stored here
    include=["app.tasks.ingest_task"],  # register task modules
)

celery_app.conf.update(
    # How long to keep task results in Redis (24 hours)
    result_expires=86400,
    # Always acknowledge the task AFTER it completes, not before.
    # This means if the worker crashes mid-task, the task goes back to queue.
    task_acks_late=True,
    # If a worker dies mid-task, put it back in the queue for another worker
    task_reject_on_worker_lost=True,
    # Serialize tasks as JSON (readable, safe)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
)
