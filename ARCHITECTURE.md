# Email Intelligence Platform - Architecture

## Overview

This is a monorepo for an email intelligence platform that generates unique email identities for website signups, receives and processes commercial emails across multiple domains, and provides AI-powered search and insights through a chatbot interface.

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         External Systems                         │
│  (Signup Service) ──► Identity API ──► Email Senders            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Email Reception Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ SMTP Server  │  │ SMTP Server  │  │ SMTP Server  │         │
│  │  (Domain 1)  │  │  (Domain 2)  │  │  (Domain N)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Processing Pipeline                          │
│  Message Queue ──► Email Parser ──► Content Extractor           │
│                         │                    │                   │
│                         ▼                    ▼                   │
│                  Metadata Store      Raw Storage (S3)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI & Search Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Embedding    │  │ Vector DB    │  │ LLM Service  │         │
│  │ Service      │  │ (Pinecone/   │  │ (Claude)     │         │
│  │              │  │  Qdrant)     │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Full-Text    │  │ Summary      │                            │
│  │ Search       │  │ Cache        │                            │
│  │ (TypeSense)  │  │              │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Identity API │  │ Search API   │  │ Chat API     │         │
│  │              │  │              │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend Layer                              │
│                    Web Chatbot UI                                │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Component Design

### 1. Monorepo Structure

```
/
├── apps/
│   ├── identity-api/          # Identity generation API
│   ├── email-receiver/        # SMTP server(s) for email reception
│   ├── email-processor/       # Email processing workers
│   ├── search-api/            # Search & retrieval API
│   ├── chat-api/              # Chatbot/LLM interface API
│   ├── web-ui/                # React/Next.js chatbot interface
│   └── admin-dashboard/       # Admin UI for monitoring
│
├── packages/
│   ├── shared-types/          # TypeScript types & interfaces
│   ├── database/              # Database schemas & migrations
│   ├── queue/                 # Message queue client/utils
│   ├── email-parser/          # Email parsing utilities
│   ├── embedding/             # Text embedding utilities
│   ├── llm-client/            # LLM API client wrapper
│   └── auth/                  # Authentication/authorization
│
├── infrastructure/
│   ├── docker/                # Docker configurations
│   ├── terraform/             # Infrastructure as Code
│   └── k8s/                   # Kubernetes manifests
│
├── scripts/
│   └── setup/                 # Development setup scripts
│
└── docs/
    └── api/                   # API documentation
```

### 2. Identity Service (`apps/identity-api`)

**Purpose**: Generate and manage unique email identities for signups

**Tech Stack**:
- Node.js/TypeScript with Fastify or Express
- PostgreSQL for identity storage
- Redis for rate limiting

**Key Features**:
- REST API endpoint: `POST /api/identities/generate`
- Generates unique identities with:
  - Unique email address (e.g., `signup-{uuid}@{domain}`)
  - Tracking metadata (website, signup date, tags)
  - Status tracking (active, paused, deleted)
- Supports multiple email domains
- API key authentication
- Rate limiting per client

**Database Schema**:
```sql
identities:
  - id (uuid, primary key)
  - email (unique, indexed)
  - domain (indexed)
  - website (string, indexed)
  - tags (jsonb)
  - status (enum: active, paused, deleted)
  - created_at
  - updated_at
  - metadata (jsonb)
```

**API Example**:
```json
POST /api/identities/generate
{
  "website": "example.com",
  "domain": "emaildomain1.com",
  "tags": ["newsletter", "promotions"]
}

Response:
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "signup-abc123@emaildomain1.com",
  "website": "example.com",
  "created_at": "2025-11-13T10:00:00Z"
}
```

### 3. Email Reception Layer (`apps/email-receiver`)

**Purpose**: Receive emails across multiple domains

**Tech Stack Options**:
1. **Custom SMTP Server**:
   - Node.js with `smtp-server` package
   - Direct control, can run multiple instances per domain

2. **Haraka**:
   - High-performance SMTP server
   - Plugin architecture
   - Good for multi-domain setups

**Architecture**:
- One SMTP server instance per domain (or shared with virtual hosting)
- Receives incoming emails via SMTP (port 25/587)
- Validates recipient against identity database
- Publishes raw email to message queue
- Handles SPF/DKIM/DMARC checking (optional)

**Flow**:
```
Email arrives → SMTP Server → Validate recipient →
  → Store raw email (S3) → Publish to queue → Acknowledge
```

### 4. Email Processing Pipeline (`apps/email-processor`)

**Purpose**: Parse, extract, and enrich email data

**Tech Stack**:
- Node.js/TypeScript workers
- BullMQ or RabbitMQ for job queue
- PostgreSQL for metadata
- S3/MinIO for raw email storage
- Redis for caching

**Processing Steps**:

1. **Email Parsing**:
   - Use `mailparser` or `postal-mime`
   - Extract headers, body (HTML/plain text), attachments
   - Parse sender, subject, date

2. **Content Extraction**:
   - Convert HTML to clean text
   - Extract links and track URLs
   - Identify email type (promotional, transactional, newsletter)
   - Extract product information, pricing, offers

3. **Metadata Storage**:
   ```sql
   emails:
     - id (uuid)
     - identity_id (fk)
     - sender (indexed)
     - subject
     - received_at (indexed)
     - email_type (indexed)
     - has_attachments
     - s3_raw_key (reference to raw storage)
     - s3_processed_key (reference to processed content)
     - metadata (jsonb: links, products, offers)
     - created_at
   ```

4. **Text Preparation for AI**:
   - Clean and normalize text
   - Chunk long emails for embedding
   - Generate summaries (for large emails)

5. **Embedding Generation**:
   - Send to embedding service
   - Store vectors in vector database

### 5. Storage Layer

**PostgreSQL** (Primary relational data):
- Identities
- Email metadata
- User sessions (if needed)
- Processing job status

**S3/MinIO** (Object storage):
- Raw email files (`.eml` format)
- Processed email content (JSON)
- Email attachments
- Organized by: `{domain}/{year}/{month}/{day}/{email-id}.eml`

**Redis**:
- Rate limiting
- Session cache
- Processing locks
- Temporary data

### 6. AI & Search Layer

#### a. Embedding Service (`packages/embedding`)

**Purpose**: Generate embeddings for semantic search

**Tech Stack**:
- OpenAI `text-embedding-3-small` or `text-embedding-3-large`
- Alternative: Open-source models via Ollama or HuggingFace

**Features**:
- Batch processing for efficiency
- Caching to avoid re-embedding
- Chunking strategy for long emails

#### b. Vector Database

**Options**:
1. **Pinecone**: Managed, easy to use, scales automatically
2. **Qdrant**: Self-hosted, fast, good for smaller scale
3. **Weaviate**: Self-hosted, built-in LLM integration

**Schema**:
```
Vector Document:
- id: email_id or chunk_id
- vector: [embedding]
- metadata: {
    email_id,
    identity_id,
    sender,
    subject,
    received_at,
    website,
    chunk_index (if chunked)
  }
```

#### c. Full-Text Search

**TypeSense** (Recommended):
- Fast, typo-tolerant
- Easy to self-host
- Good filtering capabilities

**Schema**:
```
Collection: emails
- id
- subject
- sender
- content (searchable text)
- received_at
- website
- tags[]
```

#### d. LLM Service (`packages/llm-client`)

**Purpose**: Provide AI insights, summaries, and chat

**Tech Stack**:
- Anthropic Claude API (Claude 3.5 Sonnet)
- Fallback to other providers (OpenAI, etc.)

**Features**:
- Prompt templates for:
  - Email summarization
  - Insight extraction
  - Trend analysis
  - Question answering
- Context management (RAG pattern)
- Streaming responses for chat

### 7. Search & Chat APIs

#### Search API (`apps/search-api`)

**Endpoints**:
```
GET  /api/search/emails
  - Query params: q, website, sender, date_from, date_to, limit
  - Returns: Hybrid search (vector + full-text)

GET  /api/emails/:id
  - Returns: Full email details

GET  /api/analytics/trends
  - Returns: Aggregated insights (top senders, categories, etc.)
```

**Search Strategy**:
1. **Hybrid Search**:
   - Vector similarity search (semantic)
   - Full-text keyword search
   - Combine and re-rank results

2. **Filtering**:
   - By website, sender, date range, email type
   - Support faceted search

#### Chat API (`apps/chat-api`)

**Purpose**: Chatbot interface for querying the email corpus

**Tech Stack**:
- WebSocket or SSE for streaming
- RAG (Retrieval-Augmented Generation) pattern

**Endpoints**:
```
POST /api/chat/query
  - Body: { query: string, session_id?: string }
  - Returns: Streaming response

GET  /api/chat/sessions/:id
  - Returns: Chat history
```

**Chat Flow**:
```
User Query →
  → Generate embedding →
  → Vector search (top K similar emails) →
  → Full-text search for keywords →
  → Combine & re-rank results →
  → Build context for LLM →
  → Stream LLM response with citations
```

**Example Queries**:
- "What promotional emails did I receive from Amazon last month?"
- "Summarize all the pricing changes from my SaaS subscriptions"
- "Show me trends in product launches across all retailers"

### 8. Web UI (`apps/web-ui`)

**Tech Stack**:
- Next.js 14+ (App Router)
- React
- TailwindCSS
- shadcn/ui components
- Zustand or Redux for state
- React Query for API calls

**Features**:
- Chat interface (main view)
- Email search and browse
- Identity management (view/create identities)
- Analytics dashboard
- Settings (domains, API keys)

**Key Pages**:
- `/` - Chat interface
- `/emails` - Email browser with filters
- `/identities` - Identity management
- `/analytics` - Trends and insights
- `/settings` - Configuration

### 9. Infrastructure & DevOps

#### Development Environment

**Docker Compose** (`infrastructure/docker/docker-compose.yml`):
- PostgreSQL
- Redis
- MinIO (S3-compatible storage)
- TypeSense
- Qdrant (vector DB)
- RabbitMQ
- Mailhog (SMTP testing)

#### Production Deployment

**Options**:
1. **Kubernetes** (Recommended for scale):
   - AKS, EKS, or GKE
   - Separate deployments per service
   - HPA for auto-scaling
   - Ingress for routing

2. **Docker Swarm** (Simpler alternative)

3. **Platform as a Service**:
   - Vercel/Netlify for web-ui
   - Railway/Render for APIs
   - Managed databases

**Cloud Services**:
- **Storage**: AWS S3 / GCS / Azure Blob
- **Database**: AWS RDS PostgreSQL / Supabase / Neon
- **Cache**: AWS ElastiCache / Upstash Redis
- **Queue**: AWS SQS / CloudAMQP
- **Email Reception**:
  - Self-hosted SMTP servers on EC2/Compute
  - OR use email forwarding services (e.g., CloudMailin, SendGrid Inbound Parse)

#### Email Domain Setup

**Requirements per domain**:
- MX records pointing to SMTP servers
- SPF record (optional, for validation)
- DKIM setup (optional)
- DMARC policy (optional)
- SSL/TLS certificates for SMTP

### 10. Security & Compliance

**Authentication**:
- API keys for external access (identity generation)
- JWT tokens for web UI
- OAuth for admin users (Google/GitHub)

**Data Privacy**:
- Encryption at rest (database, S3)
- Encryption in transit (TLS/SSL)
- PII handling considerations
- Data retention policies
- GDPR compliance (if applicable)

**Email Security**:
- Spam filtering (optional)
- Virus scanning for attachments
- Rate limiting on identity generation
- Suspicious activity monitoring

### 11. Monitoring & Observability

**Logging**:
- Structured JSON logging
- Centralized logging (e.g., Loki, CloudWatch, Datadog)
- Log levels: error, warn, info, debug

**Metrics**:
- Prometheus + Grafana
- Key metrics:
  - Emails received per domain
  - Processing latency
  - Queue depth
  - API response times
  - Embedding generation rate
  - LLM token usage

**Tracing**:
- OpenTelemetry
- Distributed tracing across services

**Alerting**:
- Email delivery failures
- Processing pipeline errors
- High queue depth
- Database connection issues
- API error rates

### 12. Development Workflow

**Monorepo Tools**:
- **Turborepo** or **Nx** for build orchestration
- **pnpm** for package management (workspaces)
- **TypeScript** across all packages
- **ESLint** + **Prettier** for code quality
- **Vitest** for testing

**CI/CD**:
- GitHub Actions or GitLab CI
- Pipeline stages:
  1. Lint & format check
  2. Type checking
  3. Unit tests
  4. Integration tests
  5. Build Docker images
  6. Deploy to staging
  7. E2E tests
  8. Deploy to production

## Technology Stack Summary

| Component | Technology |
|-----------|------------|
| **Runtime** | Node.js 20+ |
| **Language** | TypeScript |
| **Monorepo** | Turborepo or Nx |
| **Package Manager** | pnpm |
| **API Framework** | Fastify or Express |
| **Web Framework** | Next.js 14+ |
| **Database** | PostgreSQL 15+ |
| **Cache** | Redis 7+ |
| **Object Storage** | S3 / MinIO |
| **Message Queue** | BullMQ (Redis-based) or RabbitMQ |
| **Full-Text Search** | TypeSense |
| **Vector Database** | Qdrant or Pinecone |
| **SMTP Server** | Haraka or custom (smtp-server) |
| **LLM** | Anthropic Claude API |
| **Embeddings** | OpenAI text-embedding-3 |
| **Container** | Docker |
| **Orchestration** | Kubernetes (production) |
| **Monitoring** | Prometheus + Grafana |
| **Logging** | Pino + Loki |
| **Testing** | Vitest + Playwright |

## Scaling Considerations

### Phase 1: MVP (< 10K emails/day)
- Single SMTP server per domain
- Single processing worker
- Single database instance
- Managed vector DB (Pinecone)
- Serverless functions for APIs

### Phase 2: Growth (10K - 100K emails/day)
- Multiple SMTP server replicas with load balancing
- Horizontal scaling of processing workers
- Database read replicas
- Self-hosted Qdrant cluster
- Kubernetes deployment

### Phase 3: Scale (100K+ emails/day)
- Dedicated SMTP infrastructure per region
- Auto-scaling worker pools
- Sharded database (by domain or time)
- Distributed vector database
- CDN for static assets
- Multi-region deployment

## Development Priorities

### Week 1-2: Foundation
1. Setup monorepo structure (Turborepo + pnpm)
2. Setup development environment (Docker Compose)
3. Implement Identity API
4. Basic PostgreSQL schema

### Week 3-4: Email Reception
1. Implement SMTP server (Haraka or custom)
2. Setup message queue (BullMQ)
3. Setup S3/MinIO storage
4. Email parser package

### Week 5-6: Processing Pipeline
1. Email processing workers
2. Content extraction
3. Metadata storage
4. Integration with identity service

### Week 7-8: Search & AI
1. Setup TypeSense for full-text search
2. Setup Qdrant for vector search
3. Implement embedding generation
4. Setup LLM client

### Week 9-10: APIs
1. Search API implementation
2. Chat API with RAG
3. API documentation

### Week 11-12: Frontend
1. Next.js setup with UI components
2. Chat interface
3. Email browser
4. Identity management UI

### Week 13-14: Polish & Deploy
1. Testing (unit, integration, E2E)
2. Security hardening
3. Monitoring setup
4. Production deployment

## Open Questions & Decisions

1. **Email Volume**: Expected emails per day/month per identity?
2. **Retention**: How long to store emails? Archive strategy?
3. **Domains**: How many email domains to support initially?
4. **Authentication**: Who can generate identities? Public API or internal only?
5. **LLM Provider**: Anthropic Claude vs. OpenAI vs. self-hosted?
6. **Vector DB**: Managed (Pinecone) vs. self-hosted (Qdrant)?
7. **Deployment**: Cloud provider preference (AWS, GCP, Azure)?
8. **Budget**: Infrastructure budget for managed services?

## Next Steps

1. Review and approve architecture
2. Decide on open questions
3. Setup initial monorepo structure
4. Begin Phase 1 implementation
