"""FastAPI application for email processing"""
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from temporalio.client import Client

from app.config import settings
from app.schemas.email import EmailWebhook, EmailResponse, EmailListResponse
from app.db.database import engine, get_db
from app.models.email import Base, Email
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global Temporal client
temporal_client: Optional[Client] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application"""
    global temporal_client

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Connect to Temporal
    try:
        temporal_client = await Client.connect(settings.temporal_host)
        logger.info(f"Connected to Temporal at {settings.temporal_host}")
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {e}")
        temporal_client = None

    logger.info(f"Accepting emails for domains: {settings.domains_list}")
    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application")
    if temporal_client:
        await temporal_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security dependency
async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key from request header"""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "temporal_connected": temporal_client is not None,
        "accepted_domains": settings.domains_list,
    }

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        health_status["database_connected"] = True
    except Exception as e:
        health_status["database_connected"] = False
        health_status["database_error"] = str(e)

    return health_status


@app.post("/webhook/email", status_code=202)
async def receive_email(
    email: EmailWebhook,
    api_key: str = Depends(verify_api_key),
):
    """
    Receive email webhook from Haraka and start Temporal workflow

    Returns 202 Accepted immediately to avoid blocking Haraka
    """
    logger.info(f"Received email: {email.message_id} from {email.from_address}")

    if not temporal_client:
        logger.error("Temporal client not connected")
        raise HTTPException(status_code=503, detail="Temporal service unavailable")

    try:
        # Import here to avoid circular dependency
        from app.temporal.workflows import EmailProcessingWorkflow

        # Start workflow
        workflow_id = f"email-{email.message_id.strip('<>').replace('@', '-at-')}"

        await temporal_client.start_workflow(
            EmailProcessingWorkflow.run,
            email.model_dump(),
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        logger.info(f"Started workflow: {workflow_id}")

        return {
            "status": "accepted",
            "workflow_id": workflow_id,
            "message": "Email queued for processing",
        }

    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {str(e)}")


@app.get("/emails", response_model=EmailListResponse)
async def list_emails(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_address: Optional[str] = None,
    to_address: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List emails with optional filtering"""

    query = select(Email).order_by(desc(Email.received_at))

    # Apply filters
    if from_address:
        query = query.where(Email.from_address.ilike(f"%{from_address}%"))
    if to_address:
        query = query.where(Email.to_address.ilike(f"%{to_address}%"))
    if status:
        query = query.where(Email.status == status)

    # Get total count
    count_query = select(Email)
    if from_address:
        count_query = count_query.where(Email.from_address.ilike(f"%{from_address}%"))
    if to_address:
        count_query = count_query.where(Email.to_address.ilike(f"%{to_address}%"))
    if status:
        count_query = count_query.where(Email.status == status)

    result = await db.execute(count_query)
    total = len(result.scalars().all())

    # Get paginated results
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    emails = result.scalars().all()

    return EmailListResponse(
        emails=emails,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific email by ID"""

    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()

    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    return email
