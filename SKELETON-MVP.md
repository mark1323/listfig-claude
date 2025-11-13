# Email Intelligence Platform - MVP Skeleton

## MVP Scope

**What we're building:**
- Email reception via Haraka
- Email processing via FastAPI + Temporal workflows
- Storage in PostgreSQL
- Temporal UI for monitoring workflows

**What we're NOT building yet:**
- Identity generation API (assume emails exist)
- Search/Chat APIs
- Web UI
- Vector embeddings
- Multiple domains (just one for now)

## Directory Structure

```
listfig-claude/
├── services/
│   ├── haraka/                        # Email reception (Node.js)
│   │   ├── config/
│   │   │   ├── smtp.ini              # SMTP server config
│   │   │   ├── plugins               # List of enabled plugins
│   │   │   └── host_list             # Accepted domains
│   │   ├── plugins/
│   │   │   └── forward_to_api.js     # Custom: forward to FastAPI
│   │   ├── package.json
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   └── email-processor/               # Email processing (Python)
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py               # FastAPI app (webhook receiver)
│       │   ├── config.py             # Settings (pydantic-settings)
│       │   │
│       │   ├── models/               # SQLAlchemy models
│       │   │   ├── __init__.py
│       │   │   └── email.py          # Email model
│       │   │
│       │   ├── schemas/              # Pydantic schemas
│       │   │   ├── __init__.py
│       │   │   └── email.py          # Email schemas
│       │   │
│       │   ├── temporal/             # Temporal workflows & activities
│       │   │   ├── __init__.py
│       │   │   ├── workflows.py      # Email processing workflow
│       │   │   ├── activities.py     # Processing activities
│       │   │   └── worker.py         # Temporal worker
│       │   │
│       │   ├── services/             # Business logic
│       │   │   ├── __init__.py
│       │   │   ├── email_parser.py   # Parse email content
│       │   │   └── ai_processor.py   # AI processing (Claude API)
│       │   │
│       │   └── db/
│       │       ├── __init__.py
│       │       ├── database.py       # DB connection
│       │       └── migrations/       # Alembic migrations
│       │           ├── env.py
│       │           ├── script.py.mako
│       │           └── versions/
│       │
│       ├── tests/
│       │   ├── __init__.py
│       │   └── test_workflow.py
│       │
│       ├── pyproject.toml            # uv project file
│       ├── Dockerfile
│       └── README.md
│
├── infrastructure/
│   ├── docker/
│   │   └── docker-compose.yml        # Full dev environment
│   └── postgres/
│       └── init.sql                  # Initial DB setup
│
├── scripts/
│   ├── setup-dev.sh                  # Setup development environment
│   └── test-email.sh                 # Send test email via SMTP
│
├── .env.example                      # Environment variables template
├── .gitignore
├── README.md                         # Main documentation
├── ARCHITECTURE.md
├── ARCHITECTURE-PYTHON-STACK.md
└── SKELETON-MVP.md                   # This file
```

## Component Details

### 1. Haraka Email Receiver (`services/haraka/`)

**Purpose:** Receive emails via SMTP and forward to FastAPI

**Key Files:**

```
services/haraka/
├── config/
│   ├── smtp.ini                     # Port 25, host, max connections
│   ├── plugins                      # List: rcpt_to.in_host_list, forward_to_api
│   └── host_list                    # example.listfig.com
│
├── plugins/
│   └── forward_to_api.js           # POST email to http://email-processor:8000/webhook/email
│
├── package.json                     # Dependencies: haraka, axios
├── Dockerfile                       # Node 20, install haraka
└── README.md
```

**Flow:**
```
SMTP Email → Haraka (port 25) → Validate domain →
  → forward_to_api.js → HTTP POST → FastAPI webhook → Return 200 OK
```

### 2. Email Processor Service (`services/email-processor/`)

**Purpose:** Receive emails from Haraka, process with Temporal workflows, extract insights with AI

#### 2.1 FastAPI App (`app/main.py`)

**Endpoints:**
- `POST /webhook/email` - Receive email from Haraka, start Temporal workflow
- `GET /health` - Health check
- `GET /emails` - List emails (basic query)
- `GET /emails/{id}` - Get email details

**Responsibilities:**
- Receive webhook from Haraka
- Start Temporal workflow (fire and forget)
- Return 200 OK quickly (< 100ms)
- Provide basic read API for emails

#### 2.2 Database Models (`app/models/email.py`)

```python
# SQLAlchemy model
class Email(Base):
    __tablename__ = "emails"

    id: UUID (primary key)
    message_id: str (unique, indexed)
    from_address: str (indexed)
    to_address: str (indexed)
    subject: str
    received_at: datetime (indexed)

    # Content
    text_body: str (nullable)
    html_body: str (nullable)
    headers: dict (JSONB)

    # Processing status
    status: str (pending, processing, completed, failed)

    # AI-extracted data
    ai_summary: str (nullable)
    ai_category: str (nullable)
    ai_sentiment: str (nullable)
    ai_extracted_data: dict (JSONB, nullable)  # products, prices, offers, etc.

    # Metadata
    processing_started_at: datetime (nullable)
    processing_completed_at: datetime (nullable)
    error_message: str (nullable)

    created_at: datetime
    updated_at: datetime
```

#### 2.3 Temporal Workflow (`app/temporal/workflows.py`)

**EmailProcessingWorkflow:**

```python
@workflow.defn
class EmailProcessingWorkflow:
    @workflow.run
    async def run(self, email_data: dict) -> dict:
        """
        Process incoming email through AI pipeline

        Steps:
        1. Parse email (extract text, HTML, headers)
        2. Clean and normalize content
        3. AI Processing:
           a. Generate summary
           b. Categorize email (promotional, transactional, newsletter, etc.)
           c. Extract structured data (products, prices, offers, links)
           d. Sentiment analysis
        4. Store processed data in PostgreSQL
        5. Return processing results
        """

        # Each step is a Temporal activity with retry logic
        ...
```

**Workflow execution:**
- Timeout: 5 minutes per email
- Retry policy: 3 attempts with exponential backoff
- Each activity can be monitored in Temporal UI

#### 2.4 Temporal Activities (`app/temporal/activities.py`)

**Activities:**

1. `parse_email_activity(raw_email: dict) -> ParsedEmail`
   - Parse MIME structure
   - Extract text/HTML bodies
   - Extract headers
   - Handle attachments (skip for MVP)

2. `clean_content_activity(parsed: ParsedEmail) -> str`
   - HTML to clean text
   - Remove signatures, disclaimers
   - Normalize whitespace

3. `ai_summarize_activity(content: str) -> str`
   - Call Claude API
   - Generate concise summary (2-3 sentences)
   - Handle rate limits with retry

4. `ai_categorize_activity(content: str) -> dict`
   - Call Claude API
   - Return: category, confidence, reasoning

5. `ai_extract_data_activity(content: str, html: str) -> dict`
   - Call Claude API with structured output
   - Extract: products[], prices[], offers[], important_dates[]

6. `save_email_activity(email_data: dict) -> UUID`
   - Insert/update in PostgreSQL
   - Return email ID

**Activity options:**
- Retry: 3 attempts
- Timeout: 60 seconds each (120s for AI activities)
- Heartbeat: 10 seconds for long-running activities

#### 2.5 AI Processing Service (`app/services/ai_processor.py`)

**AIProcessor class:**

```python
class AIProcessor:
    def __init__(self, anthropic_client):
        self.client = anthropic_client

    async def summarize(self, content: str) -> str:
        """Generate 2-3 sentence summary"""

    async def categorize(self, content: str) -> dict:
        """Categorize email type"""

    async def extract_structured_data(self, content: str, html: str) -> dict:
        """Extract products, prices, offers, dates using Claude"""
```

**AI Prompts:**
- Use Claude 3.5 Sonnet
- Structured output via prompt engineering (JSON responses)
- Handle long emails (chunk if > 100K tokens)
- Cache common prompts

#### 2.6 Temporal Worker (`app/temporal/worker.py`)

**Worker setup:**
- Connects to Temporal server
- Registers workflows and activities
- Task queue: "email-processing"
- Concurrent activities: 10 (configurable)
- Runs as separate process from FastAPI

**Run as:**
```bash
python -m app.temporal.worker
```

#### 2.7 Database (`app/db/`)

**Database connection:**
- SQLAlchemy 2.0 async
- asyncpg driver
- Connection pooling
- Health checks

**Migrations (Alembic):**
- Initial: Create emails table
- Future: Add indexes, new fields

### 3. Infrastructure (`infrastructure/docker/`)

#### Docker Compose Services:

```yaml
services:
  # PostgreSQL (for emails + Temporal)
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: listfig
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ../postgres/init.sql:/docker-entrypoint-initdb.d/init.sql

  # Temporal Server
  temporal:
    image: temporalio/auto-setup:latest
    ports: ["7233:7233"]
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=postgres
      - POSTGRES_PWD=postgres
      - POSTGRES_SEEDS=postgres
    depends_on: [postgres]

  # Temporal UI
  temporal-ui:
    image: temporalio/ui:latest
    ports: ["8080:8080"]
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
    depends_on: [temporal]

  # Haraka (Email Receiver)
  haraka:
    build: ../../services/haraka
    ports: ["25:25", "587:587"]
    environment:
      - API_URL=http://email-processor:8000
      - API_KEY=${API_KEY:-dev-secret-key}
    depends_on: [email-processor]

  # Email Processor (FastAPI)
  email-processor:
    build: ../../services/email-processor
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/listfig
      - TEMPORAL_HOST=temporal:7233
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=INFO
    depends_on: [postgres, temporal]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Temporal Worker
  temporal-worker:
    build: ../../services/email-processor
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/listfig
      - TEMPORAL_HOST=temporal:7233
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=INFO
    depends_on: [postgres, temporal]
    command: python -m app.temporal.worker

volumes:
  postgres_data:
```

### 4. Configuration Files

#### `services/email-processor/pyproject.toml` (uv)

```toml
[project]
name = "email-processor"
version = "0.1.0"
description = "Email processing service with Temporal workflows"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy[asyncio]>=2.0.23",
    "asyncpg>=0.29.0",
    "alembic>=1.12.1",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "temporalio>=1.5.0",
    "anthropic>=0.8.0",
    "python-multipart>=0.0.6",
    "email-validator>=2.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "httpx>=0.25.2",
    "ruff>=0.1.6",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
]
```

#### `.env.example`

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/listfig

# Temporal
TEMPORAL_HOST=localhost:7233

# Anthropic (Claude API)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# API Security
API_KEY=dev-secret-key

# Logging
LOG_LEVEL=INFO
```

### 5. Scripts

#### `scripts/setup-dev.sh`

```bash
#!/bin/bash
# Setup development environment

# 1. Install uv if not present
# 2. Create .env from .env.example
# 3. Install Python dependencies
# 4. Start docker-compose
# 5. Run database migrations
# 6. Display access URLs
```

#### `scripts/test-email.sh`

```bash
#!/bin/bash
# Send a test email to Haraka

# Use swaks or Python smtplib to send test email
# to: test@example.listfig.com
# from: sender@example.com
# subject: Test Email
# body: This is a test email for processing
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Email Arrives via SMTP                        │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Haraka (port 25)                                                │
│  - Validate domain (example.listfig.com)                        │
│  - Extract email data                                            │
│  - HTTP POST to FastAPI webhook                                  │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Webhook (/webhook/email)                                │
│  - Receive email data                                            │
│  - Start Temporal workflow                                       │
│  - Return 200 OK immediately                                     │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Temporal Workflow: EmailProcessingWorkflow                      │
│                                                                  │
│  Step 1: Parse Email Activity                                    │
│    - Extract text, HTML, headers                                 │
│    - Output: ParsedEmail                                         │
│                                                                  │
│  Step 2: Clean Content Activity                                  │
│    - HTML → clean text                                           │
│    - Remove noise                                                │
│    - Output: clean_text                                          │
│                                                                  │
│  Step 3: AI Summarize Activity                                   │
│    - Call Claude API                                             │
│    - Generate summary                                            │
│    - Output: summary (string)                                    │
│                                                                  │
│  Step 4: AI Categorize Activity                                  │
│    - Call Claude API                                             │
│    - Determine category                                          │
│    - Output: {category, confidence}                              │
│                                                                  │
│  Step 5: AI Extract Data Activity                                │
│    - Call Claude API with structured prompt                      │
│    - Extract products, prices, offers                            │
│    - Output: {products[], prices[], offers[]}                    │
│                                                                  │
│  Step 6: Save Email Activity                                     │
│    - Insert into PostgreSQL                                      │
│    - Update status: completed                                    │
│    - Output: email_id                                            │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL Database                                             │
│  - Email stored with AI-extracted data                          │
│  - Ready for querying                                            │
└─────────────────────────────────────────────────────────────────┘
```

## API Examples

### Haraka → FastAPI Webhook

**Request:**
```http
POST /webhook/email HTTP/1.1
Host: email-processor:8000
Content-Type: application/json
X-API-Key: dev-secret-key

{
  "message_id": "<abc123@example.com>",
  "from": "sender@example.com",
  "to": ["test@example.listfig.com"],
  "subject": "20% Off Winter Sale - Limited Time!",
  "headers": {
    "date": "Wed, 13 Nov 2024 10:00:00 -0500",
    "content-type": "multipart/alternative"
  },
  "text": "Get 20% off all winter items...",
  "html": "<html><body><h1>20% Off Winter Sale</h1>...</body></html>",
  "received_at": "2024-11-13T15:00:00Z"
}
```

**Response:**
```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "status": "accepted",
  "workflow_id": "email-processing-abc123",
  "message": "Email queued for processing"
}
```

### Query Processed Emails

**Request:**
```http
GET /emails?limit=10&from=sender@example.com
```

**Response:**
```json
{
  "emails": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "message_id": "<abc123@example.com>",
      "from_address": "sender@example.com",
      "to_address": "test@example.listfig.com",
      "subject": "20% Off Winter Sale - Limited Time!",
      "received_at": "2024-11-13T15:00:00Z",
      "status": "completed",
      "ai_summary": "Promotional email offering 20% discount on winter clothing and accessories. Sale ends this weekend.",
      "ai_category": "promotional",
      "ai_sentiment": "positive",
      "ai_extracted_data": {
        "offers": [
          {
            "type": "percentage_discount",
            "value": 20,
            "products": ["winter clothing", "accessories"],
            "expiry": "2024-11-17"
          }
        ],
        "products": ["winter jackets", "scarves", "gloves"],
        "links": [
          "https://example.com/winter-sale"
        ]
      },
      "created_at": "2024-11-13T15:00:01Z"
    }
  ],
  "total": 1
}
```

## Monitoring

### Temporal UI
- URL: http://localhost:8080
- View all workflows
- See execution history
- Debug failed workflows
- Replay workflows

### Logs
- FastAPI: JSON structured logs
- Temporal Worker: Workflow execution logs
- Haraka: SMTP transaction logs

### Health Checks
- `GET /health` - FastAPI health
- Check Temporal connection
- Check PostgreSQL connection

## Development Workflow

### 1. First Time Setup
```bash
# Clone repo
git clone <repo>
cd listfig-claude

# Setup environment
./scripts/setup-dev.sh

# This will:
# - Install uv
# - Install dependencies
# - Start docker-compose
# - Run migrations
# - Show access URLs
```

### 2. Daily Development
```bash
# Start services
cd infrastructure/docker
docker-compose up -d

# Watch logs
docker-compose logs -f email-processor temporal-worker

# Access Temporal UI
open http://localhost:8080

# Send test email
./scripts/test-email.sh
```

### 3. Testing
```bash
# Unit tests
cd services/email-processor
uv run pytest

# Integration test
./scripts/test-email.sh
# Check Temporal UI for workflow execution
# Check PostgreSQL for stored email
```

## Success Criteria

**MVP is complete when:**
1. ✅ Can receive email via SMTP (Haraka)
2. ✅ Email triggers Temporal workflow
3. ✅ Workflow processes email through AI pipeline
4. ✅ AI extracts: summary, category, structured data
5. ✅ Email stored in PostgreSQL with AI data
6. ✅ Can query emails via API
7. ✅ Can monitor workflows in Temporal UI
8. ✅ All components run in docker-compose

## What's NOT in MVP

- ❌ Identity generation API
- ❌ Multiple email domains
- ❌ Vector embeddings / semantic search
- ❌ Chat interface
- ❌ Web UI
- ❌ User authentication
- ❌ Rate limiting
- ❌ Production deployment
- ❌ Comprehensive error handling
- ❌ Attachment processing
- ❌ Email threading
- ❌ Scheduled jobs (analytics, cleanup)

## File Count Summary

**Total files to create: ~35**

Breakdown:
- Haraka: 7 files
- Email Processor: 20 files
- Infrastructure: 3 files
- Scripts: 2 files
- Root: 3 files (.env.example, .gitignore, README.md)

## Next Steps After MVP

1. Add identity generation API
2. Add vector embeddings (Qdrant)
3. Add search API with hybrid search
4. Add chat API with RAG
5. Build Svelte UI
6. Add authentication
7. Production deployment

---

## Questions Before We Code

1. **Anthropic API Key**: Do you have one, or should we mock AI responses for now?
2. **Email Domain**: What domain should we use? (e.g., `emails.listfig.com`)
3. **AI Processing Depth**: For MVP, should we do full extraction or just summary + category?
4. **Local Development**: Do you have Docker installed?
5. **Python Version**: 3.11 or 3.12?

Ready to build this? 🚀
