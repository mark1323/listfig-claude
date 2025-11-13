# Email Intelligence Platform - Python Stack Architecture

## Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **API Framework** | FastAPI | Async, fast, auto-docs, type hints |
| **Language** | Python 3.11+ | Great async, rich ecosystem |
| **Web Framework** | Svelte (SPA) | Lightweight, reactive, fast |
| **SMTP Server** | Haraka (Node.js) | Best-in-class email reception |
| **Workflow Engine** | Temporal.io (self-hosted) | Durable workflows, retry logic |
| **Database** | PostgreSQL 15+ | Primary data store |
| **Cache** | Redis 7+ | Caching, session storage |
| **Object Storage** | S3 / MinIO | Email storage |
| **Full-Text Search** | TypeSense | Fast, typo-tolerant |
| **Vector Database** | Qdrant | Self-hosted vector search |
| **LLM** | Anthropic Claude API | Chat and insights |
| **Embeddings** | OpenAI API or sentence-transformers | Text embeddings |
| **ORM** | SQLAlchemy 2.0 + Alembic | Database migrations |
| **Validation** | Pydantic v2 | Data validation, serialization |
| **Package Manager** | Poetry or uv | Dependency management |
| **Monorepo** | Turborepo (Node.js tool) | Build orchestration |
| **Container** | Docker | Containerization |
| **Testing** | pytest + Playwright | Backend and E2E tests |

## Monorepo Structure

```
/
├── services/
│   ├── identity-api/          # FastAPI - Identity generation
│   ├── email-receiver/        # Haraka (Node.js) - SMTP server
│   ├── email-processor/       # Python - Temporal workers
│   ├── search-api/            # FastAPI - Search & retrieval
│   ├── chat-api/              # FastAPI - Chat with SSE
│   └── admin-api/             # FastAPI - Admin operations
│
├── workers/
│   ├── temporal-workers/      # Python Temporal workers
│   └── scheduled-jobs/        # Cron-like jobs via Temporal
│
├── packages/
│   ├── shared-types/          # Python - Pydantic models
│   ├── database/              # SQLAlchemy models & Alembic migrations
│   ├── email-parser/          # Python - Email parsing utilities
│   ├── embedding/             # Python - Embedding generation
│   ├── llm-client/            # Python - LLM API wrapper
│   └── temporal-workflows/    # Temporal workflow definitions
│
├── web/
│   └── ui/                    # Svelte SPA
│       ├── src/
│       │   ├── lib/           # Reusable components
│       │   ├── routes/        # Page components
│       │   ├── stores/        # Svelte stores (state)
│       │   ├── api/           # API client
│       │   └── App.svelte
│       ├── public/
│       └── package.json
│
├── infrastructure/
│   ├── docker/                # Docker Compose files
│   ├── temporal/              # Temporal configuration
│   └── k8s/                   # Kubernetes manifests
│
├── scripts/
│   └── setup/                 # Dev environment setup
│
└── docs/
```

## Detailed Architecture

### 1. Identity API (Python + FastAPI)

**Stack:**
- FastAPI with async PostgreSQL (asyncpg)
- Pydantic for validation
- SQLAlchemy 2.0 (async mode)

**Structure:**
```
services/identity-api/
├── app/
│   ├── main.py              # FastAPI app
│   ├── api/
│   │   └── v1/
│   │       └── identities.py
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── core/
│       ├── config.py
│       └── database.py
├── tests/
├── pyproject.toml           # Poetry dependencies
└── Dockerfile
```

**Example Code:**
```python
# app/api/v1/identities.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.identity import IdentityCreate, IdentityResponse
from app.services.identity import IdentityService
from app.core.database import get_db

router = APIRouter()

@router.post("/generate", response_model=IdentityResponse)
async def generate_identity(
    identity: IdentityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Generate a unique email identity for a signup"""
    service = IdentityService(db)
    return await service.create_identity(identity)
```

```python
# app/schemas/identity.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

class IdentityCreate(BaseModel):
    website: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    tags: list[str] = Field(default_factory=list)

class IdentityResponse(BaseModel):
    id: UUID
    email: EmailStr
    website: str
    domain: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### 2. Email Receiver (Haraka - Node.js)

**Why Haraka with Python backend?**
- Haraka is the best SMTP server (high performance, battle-tested)
- Python's SMTP options (aiosmtpd) are not production-grade
- Haraka can easily forward to Python via:
  - HTTP webhook
  - Message queue (RabbitMQ/Redis)
  - Direct socket connection

**Architecture:**
```
Incoming Email → Haraka (SMTP) → HTTP POST → FastAPI Webhook → Temporal Workflow
```

**Haraka Setup:**
```
services/email-receiver/
├── config/
│   ├── smtp.ini            # SMTP settings
│   ├── plugins             # Enabled plugins
│   └── domains             # Accepted domains
├── plugins/
│   └── process_email.js    # Custom plugin to forward to Python
├── package.json
└── Dockerfile
```

**Custom Haraka Plugin (process_email.js):**
```javascript
// Forward emails to Python FastAPI webhook
const axios = require('axios');

exports.hook_queue = async function (next, connection) {
    const transaction = connection.transaction;
    const email = {
        from: transaction.mail_from.address(),
        to: transaction.rcpt_to.map(addr => addr.address()),
        headers: transaction.header.headers_decoded,
        body: transaction.body.bodytext,
        received_at: new Date().toISOString()
    };

    try {
        await axios.post(
            process.env.EMAIL_WEBHOOK_URL || 'http://email-processor:8001/webhook/email',
            email,
            {
                timeout: 5000,
                headers: { 'X-API-Key': process.env.API_KEY }
            }
        );
        next(OK);
    } catch (err) {
        connection.logerror(`Failed to forward email: ${err.message}`);
        next(DENYSOFT, 'Temporary error processing email');
    }
};
```

**Haraka Features:**
- Multi-domain support (virtual hosting)
- SPF/DKIM/DMARC validation
- Rate limiting
- Greylisting
- Spam filtering (SpamAssassin integration)
- TLS/SSL support
- High throughput (10K+ emails/sec)

### 3. Email Processor (Python + Temporal)

**Stack:**
- Temporal Python SDK
- Email parsing: `email` stdlib + `beautifulsoup4` for HTML
- Storage client: `boto3` for S3

**Structure:**
```
services/email-processor/
├── app/
│   ├── main.py                    # FastAPI webhook receiver
│   ├── workflows/
│   │   └── email_processing.py    # Temporal workflow
│   ├── activities/
│   │   ├── parse.py               # Email parsing
│   │   ├── storage.py             # S3 storage
│   │   ├── embedding.py           # Generate embeddings
│   │   └── indexing.py            # Index in search engines
│   └── worker.py                  # Temporal worker
├── tests/
└── pyproject.toml
```

**Temporal Workflow Example:**
```python
# app/workflows/email_processing.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from app.activities import (
    parse_email,
    store_raw_email,
    extract_content,
    generate_embeddings,
    store_in_vector_db,
    index_in_typesense,
    update_metadata
)

@workflow.defn
class EmailProcessingWorkflow:
    @workflow.run
    async def run(self, email_data: dict) -> dict:
        """Process incoming email through the entire pipeline"""

        # Activity options with retry policy
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=5),
            "retry_policy": RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(minutes=1),
                backoff_coefficient=2.0,
            )
        }

        # Step 1: Store raw email in S3
        s3_key = await workflow.execute_activity(
            store_raw_email,
            email_data,
            **activity_options
        )

        # Step 2: Parse email
        parsed = await workflow.execute_activity(
            parse_email,
            email_data,
            **activity_options
        )

        # Step 3: Extract and clean content
        content = await workflow.execute_activity(
            extract_content,
            parsed,
            **activity_options
        )

        # Step 4: Generate embeddings
        embeddings = await workflow.execute_activity(
            generate_embeddings,
            content,
            **{**activity_options, "start_to_close_timeout": timedelta(minutes=10)}
        )

        # Step 5: Store in vector database
        await workflow.execute_activity(
            store_in_vector_db,
            {"email_id": parsed["id"], "embeddings": embeddings},
            **activity_options
        )

        # Step 6: Index in TypeSense for full-text search
        await workflow.execute_activity(
            index_in_typesense,
            {"email_id": parsed["id"], "content": content},
            **activity_options
        )

        # Step 7: Update metadata in PostgreSQL
        result = await workflow.execute_activity(
            update_metadata,
            {"email_id": parsed["id"], "s3_key": s3_key, "status": "completed"},
            **activity_options
        )

        return result
```

**Activity Example:**
```python
# app/activities/embedding.py
from temporalio import activity
import openai
from typing import List

@activity.defn
async def generate_embeddings(content: dict) -> List[dict]:
    """Generate embeddings for email content"""

    # Chunk content if too long
    chunks = chunk_text(content["text"], max_tokens=8000)

    embeddings = []
    for i, chunk in enumerate(chunks):
        response = await openai.Embedding.acreate(
            model="text-embedding-3-small",
            input=chunk
        )
        embeddings.append({
            "chunk_index": i,
            "text": chunk,
            "embedding": response['data'][0]['embedding']
        })

    return embeddings

def chunk_text(text: str, max_tokens: int) -> List[str]:
    """Split text into chunks for embedding"""
    # Simple chunking by sentences
    sentences = text.split('. ')
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence.split())
        if current_length + sentence_length > max_tokens:
            chunks.append('. '.join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_length
        else:
            current_chunk.append(sentence)
            current_length += sentence_length

    if current_chunk:
        chunks.append('. '.join(current_chunk))

    return chunks
```

**Temporal Worker:**
```python
# app/worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.email_processing import EmailProcessingWorkflow
from app.activities import (
    parse_email, store_raw_email, extract_content,
    generate_embeddings, store_in_vector_db, index_in_typesense,
    update_metadata
)

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="email-processing",
        workflows=[EmailProcessingWorkflow],
        activities=[
            parse_email,
            store_raw_email,
            extract_content,
            generate_embeddings,
            store_in_vector_db,
            index_in_typesense,
            update_metadata
        ]
    )

    print("Worker started, processing emails...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Search API (Python + FastAPI)

**Features:**
- Hybrid search (vector + full-text)
- Result re-ranking
- Faceted filtering

**Example:**
```python
# app/api/v1/search.py
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.schemas.search import SearchRequest, SearchResponse, EmailResult
from app.services.search import SearchService

router = APIRouter()

@router.post("/emails", response_model=SearchResponse)
async def search_emails(
    query: str = Query(..., min_length=1),
    website: Optional[str] = None,
    sender: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    search_service: SearchService = Depends()
):
    """
    Hybrid search combining semantic (vector) and keyword (full-text) search
    """

    # Vector search in Qdrant
    vector_results = await search_service.vector_search(
        query=query,
        limit=limit * 2,  # Get more for re-ranking
        filters={"website": website, "sender": sender}
    )

    # Full-text search in TypeSense
    fulltext_results = await search_service.fulltext_search(
        query=query,
        limit=limit * 2,
        filters={"website": website, "sender": sender}
    )

    # Combine and re-rank results
    combined = search_service.combine_results(
        vector_results,
        fulltext_results,
        vector_weight=0.7,
        fulltext_weight=0.3
    )

    return SearchResponse(
        results=combined[:limit],
        total=len(combined)
    )
```

### 5. Chat API (Python + FastAPI + SSE)

**Features:**
- Server-Sent Events (SSE) for streaming
- RAG (Retrieval-Augmented Generation)
- Conversation history

**Example:**
```python
# app/api/v1/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from anthropic import AsyncAnthropic

from app.schemas.chat import ChatRequest
from app.services.search import SearchService
from app.services.llm import LLMService

router = APIRouter()

@router.post("/query")
async def chat_query(
    request: ChatRequest,
    search_service: SearchService = Depends(),
    llm_service: LLMService = Depends()
):
    """Stream chat response using RAG pattern"""

    async def generate():
        # Step 1: Retrieve relevant emails
        relevant_emails = await search_service.hybrid_search(
            query=request.query,
            limit=10
        )

        # Step 2: Build context for LLM
        context = llm_service.build_context(relevant_emails)

        # Step 3: Stream LLM response
        async for chunk in llm_service.stream_response(
            query=request.query,
            context=context,
            conversation_history=request.history
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

```python
# app/services/llm.py
from anthropic import AsyncAnthropic
from typing import List, AsyncGenerator

class LLMService:
    def __init__(self):
        self.client = AsyncAnthropic()

    def build_context(self, emails: List[dict]) -> str:
        """Build context from retrieved emails"""
        context_parts = []
        for i, email in enumerate(emails, 1):
            context_parts.append(
                f"Email {i}:\n"
                f"From: {email['sender']}\n"
                f"Subject: {email['subject']}\n"
                f"Date: {email['received_at']}\n"
                f"Content: {email['content'][:500]}...\n"
            )
        return "\n---\n".join(context_parts)

    async def stream_response(
        self,
        query: str,
        context: str,
        conversation_history: List[dict]
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response with RAG"""

        system_prompt = f"""You are an AI assistant helping users understand their commercial emails.

Here are relevant emails from the user's inbox:

{context}

Use these emails to answer the user's question. Cite specific emails when relevant."""

        messages = conversation_history + [{"role": "user", "content": query}]

        async with self.client.messages.stream(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

### 6. Web UI (Svelte SPA)

**Stack:**
- Svelte 4+ (not SvelteKit - just a SPA)
- Vite for bundling
- TailwindCSS for styling
- Svelte stores for state management
- EventSource for SSE (chat streaming)

**Structure:**
```
web/ui/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   │   ├── ChatWindow.svelte
│   │   │   │   ├── MessageList.svelte
│   │   │   │   └── MessageInput.svelte
│   │   │   ├── Email/
│   │   │   │   ├── EmailList.svelte
│   │   │   │   ├── EmailCard.svelte
│   │   │   │   └── EmailDetail.svelte
│   │   │   └── Identity/
│   │   │       └── IdentityManager.svelte
│   │   ├── stores/
│   │   │   ├── auth.js
│   │   │   ├── chat.js
│   │   │   └── emails.js
│   │   └── api/
│   │       ├── client.js
│   │       ├── chat.js
│   │       ├── search.js
│   │       └── identity.js
│   ├── routes/
│   │   ├── Chat.svelte
│   │   ├── Emails.svelte
│   │   ├── Identities.svelte
│   │   └── Analytics.svelte
│   ├── App.svelte
│   └── main.js
├── public/
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

**Example Component (Chat Window):**
```svelte
<!-- src/lib/components/Chat/ChatWindow.svelte -->
<script>
  import { chatStore } from '$lib/stores/chat';
  import { chatApi } from '$lib/api/chat';
  import MessageList from './MessageList.svelte';
  import MessageInput from './MessageInput.svelte';

  let messages = [];
  let isStreaming = false;

  async function sendMessage(message) {
    // Add user message
    messages = [...messages, { role: 'user', content: message }];

    // Start streaming assistant response
    isStreaming = true;
    let assistantMessage = '';

    messages = [...messages, { role: 'assistant', content: '', streaming: true }];

    const eventSource = await chatApi.streamQuery(message, messages.slice(0, -1));

    eventSource.onmessage = (event) => {
      assistantMessage += event.data;
      messages[messages.length - 1].content = assistantMessage;
      messages = messages; // Trigger reactivity
    };

    eventSource.onerror = () => {
      isStreaming = false;
      messages[messages.length - 1].streaming = false;
      messages = messages;
      eventSource.close();
    };
  }
</script>

<div class="flex flex-col h-screen">
  <div class="flex-1 overflow-y-auto p-4">
    <MessageList {messages} />
  </div>
  <div class="border-t p-4">
    <MessageInput on:send={(e) => sendMessage(e.detail)} disabled={isStreaming} />
  </div>
</div>
```

**API Client (SSE for streaming):**
```javascript
// src/lib/api/chat.js
export const chatApi = {
  streamQuery: async (query, history) => {
    const response = await fetch('http://localhost:8003/api/v1/chat/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: JSON.stringify({ query, history })
    });

    return new EventSource(response.url);
  }
};
```

### 7. Temporal Setup (Self-Hosted)

**Docker Compose for Temporal:**
```yaml
# infrastructure/docker/docker-compose.temporal.yml
version: '3.8'

services:
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_USER=temporal
      - POSTGRES_PWD=temporal
      - POSTGRES_SEEDS=postgresql
    depends_on:
      - postgresql

  temporal-ui:
    image: temporalio/ui:latest
    ports:
      - "8080:8080"
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
    depends_on:
      - temporal

  postgresql:
    image: postgres:15
    environment:
      - POSTGRES_USER=temporal
      - POSTGRES_PASSWORD=temporal
```

## Development Environment Setup

**Docker Compose (Complete Stack):**
```yaml
# infrastructure/docker/docker-compose.yml
version: '3.8'

services:
  # Email Reception (Haraka - Node.js)
  haraka:
    build: ../../services/email-receiver
    ports:
      - "25:25"
      - "587:587"
    environment:
      - EMAIL_WEBHOOK_URL=http://email-processor:8001/webhook/email
      - API_KEY=${API_KEY}
    volumes:
      - ./haraka/config:/app/config

  # Identity API (FastAPI)
  identity-api:
    build: ../../services/identity-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/identity
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  # Email Processor (FastAPI + Temporal Worker)
  email-processor:
    build: ../../services/email-processor
    ports:
      - "8001:8001"
    environment:
      - TEMPORAL_HOST=temporal:7233
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/emails
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY=minioadmin
      - S3_SECRET_KEY=minioadmin
    depends_on:
      - postgres
      - temporal
      - minio

  # Search API (FastAPI)
  search-api:
    build: ../../services/search-api
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/emails
      - TYPESENSE_URL=http://typesense:8108
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - postgres
      - typesense
      - qdrant

  # Chat API (FastAPI)
  chat-api:
    build: ../../services/chat-api
    ports:
      - "8003:8003"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SEARCH_API_URL=http://search-api:8002
    depends_on:
      - search-api

  # Web UI (Svelte SPA)
  web-ui:
    build: ../../web/ui
    ports:
      - "5173:5173"
    environment:
      - VITE_IDENTITY_API=http://localhost:8000
      - VITE_SEARCH_API=http://localhost:8002
      - VITE_CHAT_API=http://localhost:8003

  # Infrastructure
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_MULTIPLE_DATABASES=identity,emails
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  typesense:
    image: typesense/typesense:0.25.1
    ports:
      - "8108:8108"
    environment:
      - TYPESENSE_API_KEY=xyz
      - TYPESENSE_DATA_DIR=/data
    volumes:
      - typesense_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - POSTGRES_SEEDS=postgres
      - POSTGRES_USER=user
      - POSTGRES_PWD=pass
    depends_on:
      - postgres

  temporal-ui:
    image: temporalio/ui:latest
    ports:
      - "8080:8080"
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
    depends_on:
      - temporal

volumes:
  postgres_data:
  minio_data:
  typesense_data:
  qdrant_data:
```

## Python Package Management

**Using Poetry:**
```toml
# services/identity-api/pyproject.toml
[tool.poetry]
name = "identity-api"
version = "0.1.0"
description = "Identity generation service"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.23"}
asyncpg = "^0.29.0"
alembic = "^1.12.1"
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
redis = {extras = ["hiredis"], version = "^5.0.1"}

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
httpx = "^0.25.2"
black = "^23.11.0"
ruff = "^0.1.6"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Monorepo Build System

Even with Python, we can use Turborepo for orchestration:

```json
// turbo.json (at root)
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["build"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

Each Python service has a `package.json` for Turborepo:
```json
// services/identity-api/package.json
{
  "name": "@listfig/identity-api",
  "version": "1.0.0",
  "scripts": {
    "dev": "poetry run uvicorn app.main:app --reload --port 8000",
    "build": "poetry build",
    "test": "poetry run pytest",
    "lint": "poetry run ruff check .",
    "format": "poetry run black ."
  }
}
```

## Comparison: Python vs Node.js Stack

| Aspect | Python + FastAPI | Node.js + Fastify |
|--------|------------------|-------------------|
| **Performance** | Very fast (async), ~20K req/s | Very fast (event loop), ~30K req/s |
| **Language Unity** | Python backend, JS frontend (2 languages) | JS everywhere (1 language) |
| **Type Safety** | Pydantic type hints (runtime) | TypeScript (compile time) |
| **Learning Curve** | Lower for data engineers | Lower for full-stack JS devs |
| **Email Parsing** | Built-in `email` module | Multiple npm packages |
| **SMTP Server** | **Haraka (Node.js)** - same | **Haraka** - native |
| **AI/ML Libraries** | Excellent (transformers, etc.) | Limited (use APIs) |
| **Async Maturity** | Good (asyncio) | Excellent (native) |
| **Developer Experience** | Great (Poetry, pytest) | Great (pnpm, vitest) |
| **Temporal SDK** | Mature, feature-complete | Mature, feature-complete |
| **Ecosystem** | Huge for data/ML | Huge for web/APIs |

## Pros of Python Stack

✅ **Better for data processing**: Rich libraries for text processing, NLP
✅ **Familiar for data engineers**: Most ML/AI engineers know Python
✅ **Excellent type hints**: Pydantic provides runtime validation
✅ **FastAPI auto-docs**: Automatic OpenAPI/Swagger documentation
✅ **Strong AI ecosystem**: Easy to integrate local ML models if needed
✅ **Simpler syntax**: Generally more readable for complex logic

## Cons of Python Stack

⚠️ **Two languages**: Python backend + JavaScript frontend
⚠️ **No type sharing**: Can't share types between backend and frontend
⚠️ **Haraka plugin in JS**: Email receiver plugin needs Node.js anyway
⚠️ **Monorepo complexity**: Mixing Python and JS in monorepo is trickier
⚠️ **Slightly slower**: For pure I/O, Node.js edge in raw performance

## Recommendation

**Use Python + FastAPI if:**
- Team is primarily Python developers
- Plan to do local ML/NLP processing (not just API calls)
- Prefer Pydantic validation and FastAPI auto-docs
- Don't mind having JS for frontend + Haraka

**Use Node.js/TypeScript if:**
- Team knows JavaScript/TypeScript
- Want one language across entire stack
- Value compile-time type safety
- Want simpler monorepo management
- Need maximum I/O performance

**For this project**, both work well! The key decision is:
- **Python** = Better for data processing, familiar for ML engineers
- **Node.js** = Better for full-stack unity, simpler monorepo

Since you're keeping Haraka (Node.js) anyway, you'll have Node.js in your stack regardless. The question is whether you want your APIs in Python or Node.js.

## Next Steps

1. Choose: Python or Node.js for APIs?
2. Confirm: Keep Haraka for SMTP? ✅ (Yes, best-in-class)
3. Confirm: Use Temporal? ✅ (Yes, great for this use case)
4. Confirm: Svelte for UI? (vs React/Vue)
5. Begin implementation with chosen stack
