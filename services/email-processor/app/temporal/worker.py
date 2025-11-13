"""Temporal worker for executing email processing workflows"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import settings
from app.temporal.workflows import EmailProcessingWorkflow
from app.temporal.activities import (
    parse_email_activity,
    ai_process_email_activity,
    save_email_activity,
    mark_email_failed_activity,
)

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Start Temporal worker"""
    logger.info(f"Connecting to Temporal at {settings.temporal_host}")

    # Connect to Temporal
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)

    logger.info(f"Connected to Temporal namespace: {settings.temporal_namespace}")

    # Create worker
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[EmailProcessingWorkflow],
        activities=[
            parse_email_activity,
            ai_process_email_activity,
            save_email_activity,
            mark_email_failed_activity,
        ],
        max_concurrent_activities=10,
    )

    logger.info(f"Worker started on task queue: {settings.temporal_task_queue}")
    logger.info("Waiting for email processing tasks...")

    # Run worker
    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        raise
