"""Pydantic schemas for request/response validation"""
from app.schemas.email import EmailWebhook, EmailResponse, EmailListResponse

__all__ = ["EmailWebhook", "EmailResponse", "EmailListResponse"]
