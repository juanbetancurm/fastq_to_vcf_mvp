# Celery app is imported here so it is loaded when Django starts.
# This ensures @shared_task decorators work correctly.
from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
