"""Temporal activities for email processing"""
import logging
from datetime import datetime
from typing import Dict
from uuid import uuid4

from temporalio import activity
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models.email import Email, EmailStatus
from app.services.email_parser import parse_email_content
from app.services.ai_processor import AIProcessor

logger = logging.getLogger(__name__)

# Create separate engine for activities (workers run in different process)
activity_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
ActivitySessionLocal = async_sessionmaker(activity_engine, expire_on_commit=False)


@activity.defn(name="parse_email")
async def parse_email_activity(email_data: Dict) -> Dict:
    """
    Parse and clean email content

    Args:
        email_data: Raw email data from Haraka

    Returns:
        Parsed email data
    """
    activity.logger.info(f"Parsing email: {email_data.get('message_id')}")

    try:
        parsed = parse_email_content(email_data)
        activity.logger.info(f"Successfully parsed email, content length: {len(parsed['clean_content'])}")
        return parsed
    except Exception as e:
        activity.logger.error(f"Failed to parse email: {e}")
        raise


@activity.defn(name="ai_process_email")
async def ai_process_email_activity(parsed_data: Dict) -> Dict:
    """
    Process email with AI to generate summary and category

    Args:
        parsed_data: Parsed email data

    Returns:
        AI processing results (summary, category)
    """
    activity.logger.info(f"AI processing email: {parsed_data.get('message_id')}")

    try:
        ai_processor = AIProcessor()

        result = await ai_processor.process_email(
            content=parsed_data.get("clean_content", ""),
            subject=parsed_data.get("subject", ""),
        )

        activity.logger.info(f"AI processing complete: category={result['category']}")
        return result

    except Exception as e:
        activity.logger.error(f"AI processing failed: {e}")
        raise


@activity.defn(name="save_email")
async def save_email_activity(parsed_data: Dict, ai_result: Dict) -> str:
    """
    Save processed email to database

    Args:
        parsed_data: Parsed email data
        ai_result: AI processing results

    Returns:
        Email ID
    """
    message_id = parsed_data.get("message_id")
    activity.logger.info(f"Saving email to database: {message_id}")

    async with ActivitySessionLocal() as db:
        try:
            # Check if email already exists
            from sqlalchemy import select
            result = await db.execute(select(Email).where(Email.message_id == message_id))
            existing_email = result.scalar_one_or_none()

            if existing_email:
                # Update existing email
                existing_email.status = EmailStatus.COMPLETED
                existing_email.ai_summary = ai_result.get("summary")
                existing_email.ai_category = ai_result.get("category")
                existing_email.processing_completed_at = datetime.utcnow()
                existing_email.updated_at = datetime.utcnow()

                await db.commit()
                activity.logger.info(f"Updated existing email: {existing_email.id}")
                return str(existing_email.id)

            else:
                # Create new email
                email = Email(
                    id=uuid4(),
                    message_id=message_id,
                    from_address=parsed_data.get("from_address", ""),
                    to_address=parsed_data.get("to_address", ""),
                    subject=parsed_data.get("subject"),
                    text_body=parsed_data.get("text_body"),
                    html_body=parsed_data.get("html_body"),
                    headers=parsed_data.get("headers"),
                    received_at=datetime.fromisoformat(parsed_data.get("received_at").replace("Z", "+00:00")),
                    status=EmailStatus.COMPLETED,
                    ai_summary=ai_result.get("summary"),
                    ai_category=ai_result.get("category"),
                    processing_started_at=datetime.utcnow(),
                    processing_completed_at=datetime.utcnow(),
                )

                db.add(email)
                await db.commit()
                await db.refresh(email)

                activity.logger.info(f"Created new email: {email.id}")
                return str(email.id)

        except Exception as e:
            activity.logger.error(f"Failed to save email: {e}")
            await db.rollback()
            raise


@activity.defn(name="mark_email_failed")
async def mark_email_failed_activity(email_data: Dict, error: str) -> None:
    """
    Mark email as failed in database

    Args:
        email_data: Email data
        error: Error message
    """
    message_id = email_data.get("message_id")
    activity.logger.error(f"Marking email as failed: {message_id} - {error}")

    async with ActivitySessionLocal() as db:
        try:
            from sqlalchemy import select
            result = await db.execute(select(Email).where(Email.message_id == message_id))
            email = result.scalar_one_or_none()

            if email:
                email.status = EmailStatus.FAILED
                email.error_message = error
                email.updated_at = datetime.utcnow()
                await db.commit()

        except Exception as e:
            activity.logger.error(f"Failed to mark email as failed: {e}")
            await db.rollback()
