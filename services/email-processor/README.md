# Email Processor Service

FastAPI service for receiving, processing, and storing emails with AI-powered analysis.

## Overview

This service consists of two components:

1. **FastAPI Application** - Webhook receiver and query API
2. **Temporal Worker** - Background processing with workflows

## Architecture

```
Haraka → FastAPI Webhook → Temporal Workflow
                              ↓
          [Parse → AI Process → Save to DB]
                              ↓
                         PostgreSQL
```

## Running Locally

### Using Docker (Recommended)

```bash
cd infrastructure/docker
docker-compose up -d email-processor temporal-worker
```

### Using uv (Development)

```bash
cd services/email-processor

# Install dependencies
uv pip install -e .

# Run FastAPI
uvicorn app.main:app --reload --port 8000

# Run Temporal Worker (in another terminal)
python -m app.temporal.worker
```

## Configuration

Set environment variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/listfig

# Temporal
TEMPORAL_HOST=localhost:7233
TEMPORAL_TASK_QUEUE=email-processing

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4o-mini

# API Security
API_KEY=dev-secret-key

# Logging
LOG_LEVEL=INFO
```

## API Endpoints

### POST /webhook/email

Receive email from Haraka and start processing workflow.

**Headers:**
- `X-API-Key`: API key for authentication

**Body:**
```json
{
  "message_id": "<abc@example.com>",
  "from": "sender@example.com",
  "to": ["test@emails.listfig.com"],
  "subject": "Email subject",
  "text": "Plain text body",
  "html": "<html>HTML body</html>",
  "headers": {},
  "received_at": "2024-11-13T10:00:00Z"
}
```

**Response:** 202 Accepted

### GET /emails

List emails with pagination and filters.

**Query Parameters:**
- `limit` (1-100, default: 20)
- `offset` (default: 0)
- `from_address` (filter)
- `to_address` (filter)
- `status` (filter)

### GET /emails/{email_id}

Get specific email details.

### GET /health

Health check with service status.

### GET /

Service info and status.

### GET /docs

Interactive API documentation (Swagger UI).

## Temporal Workflows

### EmailProcessingWorkflow

Main workflow for processing emails.

**Activities:**
1. `parse_email` - Parse and clean email content
2. `ai_process_email` - Generate summary and category
3. `save_email` - Store in database
4. `mark_email_failed` - Handle failures

**Configuration:**
- Task Queue: `email-processing`
- Timeout: 5 minutes
- Retry: 3 attempts with exponential backoff

## Database Models

### Email

```python
class Email:
    id: UUID
    message_id: str (unique)
    from_address: str
    to_address: str
    subject: str
    text_body: str
    html_body: str
    headers: dict (JSONB)
    received_at: datetime

    # Processing
    status: EmailStatus
    ai_summary: str
    ai_category: str
    ai_metadata: dict (JSONB)

    # Timestamps
    processing_started_at: datetime
    processing_completed_at: datetime
    created_at: datetime
    updated_at: datetime
```

## AI Processing

### Summarization

Uses OpenAI GPT-4o-mini to generate 2-3 sentence summaries of emails.

**Prompt Strategy:**
- Truncate long emails to 4000 chars
- Focus on main purpose and key information
- Low temperature (0.3) for consistency

### Categorization

Classifies emails into categories:
- `promotional` - Sales, discounts, marketing
- `transactional` - Receipts, confirmations, shipping
- `newsletter` - Regular content updates
- `notification` - Alerts, reminders, system messages
- `social` - Social media notifications
- `other` - Uncategorized

## Development

### Project Structure

```
app/
├── main.py              # FastAPI application
├── config.py            # Settings & configuration
├── models/              # SQLAlchemy models
│   └── email.py
├── schemas/             # Pydantic schemas
│   └── email.py
├── services/            # Business logic
│   ├── email_parser.py
│   └── ai_processor.py
├── temporal/            # Temporal workflows
│   ├── workflows.py
│   ├── activities.py
│   └── worker.py
└── db/                  # Database utilities
    └── database.py
```

### Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking (if using mypy)
mypy app/
```

## Monitoring

### Logs

```bash
# View FastAPI logs
docker-compose logs -f email-processor

# View worker logs
docker-compose logs -f temporal-worker
```

### Temporal UI

Access at http://localhost:8080 to:
- View workflow executions
- Debug failed workflows
- Replay workflows
- Monitor activity execution

### Database Queries

```sql
-- Recent emails
SELECT id, from_address, subject, ai_category, status
FROM emails
ORDER BY received_at DESC
LIMIT 10;

-- Failed emails
SELECT id, message_id, error_message
FROM emails
WHERE status = 'failed';

-- Category distribution
SELECT ai_category, COUNT(*)
FROM emails
GROUP BY ai_category
ORDER BY COUNT(*) DESC;
```

## Troubleshooting

### Workflow not starting

1. Check Temporal connection in logs
2. Verify Temporal server is running
3. Check API key in webhook request

### AI processing failing

1. Verify OpenAI API key is valid
2. Check rate limits (wait and retry)
3. Review worker logs for errors

### Database connection issues

1. Verify DATABASE_URL is correct
2. Check PostgreSQL is running
3. Verify network connectivity

## Performance Considerations

- **Concurrent Activities**: Worker runs max 10 activities concurrently
- **Connection Pooling**: Database pool size = 10, max overflow = 20
- **Retry Logic**: 3 attempts with exponential backoff
- **Timeouts**: Parse (120s), AI (180s), Save (120s)

## Security

- API key authentication on webhook endpoint
- Environment-based configuration
- Database connection encryption (in production)
- No sensitive data in logs

## Production Checklist

- [ ] Change API_KEY from default
- [ ] Use production-grade database (AWS RDS, etc.)
- [ ] Setup proper logging (structured JSON)
- [ ] Configure SSL/TLS for API
- [ ] Setup monitoring and alerting
- [ ] Configure rate limiting
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Setup database backups
- [ ] Configure auto-scaling for workers
- [ ] Enable Temporal archival for old workflows
