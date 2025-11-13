"""AI processing service using OpenAI"""
import logging
from typing import Dict, Optional
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class AIProcessor:
    """AI processor for email analysis using OpenAI"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def summarize_email(self, content: str, subject: str) -> str:
        """
        Generate a concise summary of the email

        Args:
            content: Email content
            subject: Email subject

        Returns:
            2-3 sentence summary
        """
        if not content or len(content.strip()) < 10:
            return "Email has no meaningful content."

        # Truncate very long emails for token efficiency
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        prompt = f"""Summarize this email in 2-3 concise sentences. Focus on the main purpose and key information.

Subject: {subject}

Email content:
{content}

Summary:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes emails concisely.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Failed to generate summary: {str(e)}"

    async def categorize_email(self, content: str, subject: str) -> str:
        """
        Categorize the email type

        Args:
            content: Email content
            subject: Email subject

        Returns:
            Category (promotional, transactional, newsletter, notification, other)
        """
        if not content:
            return "unknown"

        # Truncate for efficiency
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        prompt = f"""Categorize this email into ONE of these categories:
- promotional (sales, discounts, marketing)
- transactional (receipts, confirmations, shipping updates)
- newsletter (regular content updates, news)
- notification (alerts, reminders, system messages)
- social (social media notifications, comments)
- other (doesn't fit above categories)

Subject: {subject}

Email content:
{content}

Category (one word only):"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that categorizes emails. Respond with only the category name.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=10,
                temperature=0.1,
            )

            category = response.choices[0].message.content.strip().lower()
            logger.info(f"Categorized email as: {category}")

            # Validate category
            valid_categories = ["promotional", "transactional", "newsletter", "notification", "social", "other"]
            if category not in valid_categories:
                category = "other"

            return category

        except Exception as e:
            logger.error(f"Failed to categorize email: {e}")
            return "unknown"

    async def process_email(self, content: str, subject: str) -> Dict:
        """
        Process email with AI (summary + category)

        Args:
            content: Email content
            subject: Email subject

        Returns:
            Dictionary with summary and category
        """
        # Run both in parallel for efficiency
        import asyncio

        summary_task = self.summarize_email(content, subject)
        category_task = self.categorize_email(content, subject)

        summary, category = await asyncio.gather(summary_task, category_task)

        return {
            "summary": summary,
            "category": category,
        }
