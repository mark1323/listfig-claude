"""Temporal workflows for email processing"""
from datetime import timedelta
from typing import Dict

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        parse_email_activity,
        ai_process_email_activity,
        save_email_activity,
        mark_email_failed_activity,
    )


@workflow.defn(name="EmailProcessingWorkflow")
class EmailProcessingWorkflow:
    """
    Workflow for processing incoming emails

    Steps:
    1. Parse email content
    2. AI processing (summary + category)
    3. Save to database
    """

    @workflow.run
    async def run(self, email_data: Dict) -> Dict:
        """
        Execute email processing workflow

        Args:
            email_data: Raw email data from Haraka

        Returns:
            Processing result with email_id
        """
        workflow.logger.info(f"Starting email processing workflow: {email_data.get('message_id')}")

        # Activity options with retry policy
        activity_options = workflow.ActivityOptions(
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=30),
                backoff_coefficient=2.0,
            ),
        )

        try:
            # Step 1: Parse email
            workflow.logger.info("Step 1: Parsing email...")
            parsed_data = await workflow.execute_activity(
                parse_email_activity,
                email_data,
                **activity_options,
            )

            # Step 2: AI processing
            workflow.logger.info("Step 2: AI processing...")
            ai_result = await workflow.execute_activity(
                ai_process_email_activity,
                parsed_data,
                **{**activity_options, "start_to_close_timeout": timedelta(seconds=180)},
            )

            # Step 3: Save to database
            workflow.logger.info("Step 3: Saving to database...")
            email_id = await workflow.execute_activity(
                save_email_activity,
                args=[parsed_data, ai_result],
                **activity_options,
            )

            workflow.logger.info(f"Email processing completed successfully: {email_id}")

            return {
                "status": "completed",
                "email_id": email_id,
                "summary": ai_result.get("summary"),
                "category": ai_result.get("category"),
            }

        except Exception as e:
            workflow.logger.error(f"Email processing failed: {e}")

            # Mark as failed in database
            try:
                await workflow.execute_activity(
                    mark_email_failed_activity,
                    args=[email_data, str(e)],
                    **activity_options,
                )
            except Exception as mark_error:
                workflow.logger.error(f"Failed to mark email as failed: {mark_error}")

            return {
                "status": "failed",
                "error": str(e),
            }
