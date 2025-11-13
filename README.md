# Listfig Email Intelligence Platform - MVP

An email intelligence platform that receives commercial emails, processes them with AI, and stores insights for analysis.

## Features

- **Multi-domain email reception** via Haraka SMTP server
- **AI-powered processing** using OpenAI (GPT-4o-mini)
  - Email summarization
  - Automatic categorization (promotional, transactional, newsletter, etc.)
- **Durable workflows** with Temporal.io for reliable processing
- **FastAPI backend** with async PostgreSQL
- **Real-time monitoring** via Temporal UI

## Architecture

```
Email → Haraka SMTP → FastAPI Webhook → Temporal Workflow
                                            ↓
                        [Parse → AI Process → Save to DB]
                                            ↓
                                      PostgreSQL
```

### Components

- **Haraka** (Node.js): Best-in-class SMTP server for receiving emails
- **Email Processor** (Python/FastAPI): Webhook receiver and API
- **Temporal Worker** (Python): Background workflow execution
- **PostgreSQL**: Email storage and Temporal backend
- **OpenAI API**: AI processing (summarization & categorization)

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API key
- Python 3.11+ (for test scripts)

### Setup

1. **Clone and setup**
   ```bash
   git clone <repo>
   cd listfig-claude
   ./scripts/setup-dev.sh
   ```

2. **Configure API key**
   Edit `.env` and add your OpenAI API key:
   ```bash
   OPENAI_API_KEY=sk-proj-xxxxx
   ```

3. **Start services**
   ```bash
   cd infrastructure/docker
   docker-compose up -d
   ```

4. **Send test email**
   ```bash
   ./scripts/test-email.sh
   ```

### Access URLs

- **Email Processor API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8080
- **SMTP Server**: localhost:2525

## Usage

### Send Email via SMTP

```bash
# Using the test script
./scripts/test-email.sh

# Using swaks (if installed)
swaks --to test@emails.listfig.com \
      --from sender@example.com \
      --server localhost:2525 \
      --body "Your email content"
```

### Query Processed Emails

```bash
# List all emails
curl http://localhost:8000/emails

# Filter by sender
curl http://localhost:8000/emails?from_address=example.com

# Get specific email
curl http://localhost:8000/emails/{email_id}
```

### Monitor Workflow Execution

1. Open Temporal UI: http://localhost:8080
2. Find your workflow by message ID
3. See execution history, activity results, and any errors

## Email Domains

The system accepts emails for domains configured in `.env`:

```bash
EMAIL_DOMAINS=emails.listfig.com,mail.listfig.com,inbox.listfig.com
```

Add domains to `services/haraka/config/host_list`:
```
emails.listfig.com
mail.listfig.com
```

## Development

### View Logs

```bash
cd infrastructure/docker

# All services
docker-compose logs -f

# Specific service
docker-compose logs -f email-processor
docker-compose logs -f temporal-worker
docker-compose logs -f haraka
```

### Restart Services

```bash
cd infrastructure/docker

# Restart all
docker-compose restart

# Restart specific service
docker-compose restart email-processor
```

### Stop Services

```bash
cd infrastructure/docker
docker-compose down

# With volume cleanup
docker-compose down -v
```

### Access Database

```bash
# PostgreSQL CLI
docker-compose exec postgres psql -U postgres -d listfig

# View emails
SELECT id, from_address, subject, ai_category, ai_summary
FROM emails
ORDER BY created_at DESC
LIMIT 10;
```

## Project Structure

```
listfig-claude/
├── services/
│   ├── haraka/              # SMTP email receiver
│   └── email-processor/     # FastAPI + Temporal workers
├── infrastructure/
│   ├── docker/              # Docker Compose setup
│   └── postgres/            # Database initialization
├── scripts/
│   ├── setup-dev.sh         # Development setup
│   └── test-email.sh        # Send test email
└── docs/
    ├── ARCHITECTURE.md      # Full architecture docs
    └── SKELETON-MVP.md      # MVP specification
```

## API Reference

### POST /webhook/email

Receive email from Haraka (internal use).

**Request:**
```json
{
  "message_id": "<abc@example.com>",
  "from": "sender@example.com",
  "to": ["test@emails.listfig.com"],
  "subject": "Test Email",
  "text": "Plain text body",
  "html": "<html>HTML body</html>",
  "received_at": "2024-11-13T10:00:00Z"
}
```

**Response:** 202 Accepted

### GET /emails

List processed emails with optional filters.

**Query Parameters:**
- `limit` (default: 20, max: 100)
- `offset` (default: 0)
- `from_address` (filter by sender)
- `to_address` (filter by recipient)
- `status` (pending, processing, completed, failed)

**Response:**
```json
{
  "emails": [
    {
      "id": "uuid",
      "message_id": "<abc@example.com>",
      "from_address": "sender@example.com",
      "to_address": "test@emails.listfig.com",
      "subject": "Test Email",
      "received_at": "2024-11-13T10:00:00Z",
      "status": "completed",
      "ai_summary": "This is a test email...",
      "ai_category": "transactional",
      "created_at": "2024-11-13T10:00:01Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### GET /emails/{email_id}

Get a specific email by ID.

**Response:** Same as individual email object above.

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "temporal_connected": true,
  "database_connected": true,
  "accepted_domains": ["emails.listfig.com"]
}
```

## Workflow Details

### EmailProcessingWorkflow

**Steps:**
1. **Parse Email** - Extract and clean content from HTML/text
2. **AI Processing** - Generate summary and category using OpenAI
3. **Save to DB** - Store processed email with AI insights

**Retry Policy:**
- Maximum attempts: 3
- Initial interval: 1 second
- Maximum interval: 30 seconds
- Backoff coefficient: 2.0

**Timeouts:**
- Parse: 120 seconds
- AI Processing: 180 seconds
- Save: 120 seconds

## Troubleshooting

### Email not being processed

1. Check Haraka logs:
   ```bash
   docker-compose logs haraka
   ```

2. Check if email-processor received webhook:
   ```bash
   docker-compose logs email-processor | grep "Received email"
   ```

3. Check Temporal UI for workflow status:
   http://localhost:8080

### AI processing failing

1. Verify OpenAI API key in `.env`
2. Check temporal-worker logs:
   ```bash
   docker-compose logs temporal-worker
   ```

### Services not starting

1. Check Docker logs:
   ```bash
   docker-compose logs
   ```

2. Verify ports are available (8000, 2525, 5432, 7233, 8080)

3. Restart services:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## What's Next

This is the MVP. Future enhancements:

- [ ] Identity generation API for creating unique email addresses
- [ ] Vector embeddings for semantic search
- [ ] Search API with hybrid search (keyword + semantic)
- [ ] Chat API with RAG for asking questions about emails
- [ ] Svelte web UI
- [ ] Product/offer extraction from emails
- [ ] Email threading and conversation tracking
- [ ] Scheduled analytics jobs
- [ ] Rate limiting and authentication
- [ ] Production deployment configuration

## Contributing

See architecture documents:
- `ARCHITECTURE.md` - Full system architecture
- `ARCHITECTURE-PYTHON-STACK.md` - Python stack details
- `SKELETON-MVP.md` - MVP specification

## License

[Your License Here]
