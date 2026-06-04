# Periskope WhatsApp Outbound Campaign Automation

A production-ready Python framework for sending WhatsApp messages at scale via Periskope API. Built with FastAPI, modular agents, and error handling.

**Status:** v1.0 (Send-focused) | **v2.0:** Fetch/analytics coming soon

---

## Quick Start

### Prerequisites
- Python 3.11+
- Periskope API credentials (API key, Account ID, Workspace ID)
- VS Code (recommended)

### Installation

```bash
# Clone/extract this folder
cd periskope-whatsapp-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy env template and configure
cp .env.example .env
# Edit .env with your Periskope API credentials
```

### Run the Server

```bash
uvicorn main:app --reload --port 8000
```

Visit: `http://localhost:8000/docs` (interactive API docs)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   POST /     │  │   GET /      │  │   POST /     │     │
│  │   send       │  │   fetch      │  │   batch      │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
├─────────┼──────────────────┼──────────────────┼─────────────┤
│         │                  │                  │             │
│  ┌──────▼────┐  ┌─────────▼──┐  ┌───────────▼────┐         │
│  │  Agent 1  │  │  Agent 4   │  │  Agent 1+3     │         │
│  │  Message  │  │  Periskope │  │  (sequence)    │         │
│  │  Builder  │  │  Fetcher   │  │                │         │
│  └──────┬────┘  └─────────┬──┘  └────────────────┘         │
│         │                  │                               │
│  ┌──────▼────────────┬─────▼────────────────────┐          │
│  │  Agent 2          │                          │          │
│  │  Recipient        │   Agent 5 (Error Handler)          │
│  │  Validator        │   (Logging + Claude CLI) │          │
│  └──────┬────────────┴─────────────────────────┘          │
│         │                                                  │
│  ┌──────▼──────────────────────────────┐                  │
│  │       Agent 3                        │                  │
│  │       Periskope Sender               │                  │
│  │       (HTTP POST to Periskope API)   │                  │
│  └──────────────────────────────────────┘                  │
│         │                                                  │
└─────────┼──────────────────────────────────────────────────┘
          │
          ▼
    ┌──────────────────┐
    │  Periskope API   │
    │  (WhatsApp msgs) │
    └──────────────────┘
```

---

## Folder Structure

```
periskope-whatsapp-automation/
│
├── README.md                   ← You are here
├── requirements.txt            ← Python dependencies
├── .env.example                ← Copy to .env and configure
├── main.py                     ← FastAPI app entry point
│
├── config/
│   ├── __init__.py
│   ├── settings.py             ← Config management, env vars
│   └── constants.py            ← API endpoints, defaults
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py           ← Base class (all agents inherit from this)
│   ├── message_builder.py       ← Agent 1: Template + personalization
│   ├── recipient_validator.py   ← Agent 2: Phone validation
│   ├── periskope_sender.py      ← Agent 3: Send via Periskope API
│   ├── periskope_fetcher.py     ← Agent 4: Fetch sent messages (v2)
│   └── error_handler.py         ← Agent 5: Error logging + Claude CLI
│
├── schemas/
│   ├── __init__.py
│   ├── message.py              ← Pydantic: SendRequest, MessagePayload
│   └── contact.py              ← Pydantic: ContactData, BatchUpload
│
├── api/
│   ├── __init__.py
│   ├── routes.py               ← FastAPI endpoints (POST /send, GET /fetch, etc.)
│   └── middleware.py           ← Auth, logging middleware
│
├── utils/
│   ├── __init__.py
│   ├── logger.py               ← Structured logging
│   ├── validators.py           ← Phone regex, email validation
│   └── csv_parser.py           ← Parse batch CSV uploads
│
├── database/
│   ├── __init__.py
│   └── models.py               ← SQLite models (MessageLog, DeliveryStatus)
│
├── templates/
│   └── message_templates.json   ← Pre-built message templates library
│
└── tests/
    ├── __init__.py
    ├── test_agents.py          ← Unit tests for each agent
    ├── test_message_builder.py  ← Message builder edge cases
    └── mock_periskope.py        ← Mock Periskope API for testing
```

---

## Agent Responsibilities

| Agent | Module | Input | Output | Skills |
|-------|--------|-------|--------|--------|
| **1: Message Builder** | `message_builder.py` | Template + contact dict | Personalized message text | String interpolation, variable substitution |
| **2: Recipient Validator** | `recipient_validator.py` | Phone number(s) | Valid/invalid list with reasons | Regex validation, format checking |
| **3: Periskope Sender** | `periskope_sender.py` | Message + phone + API key | Send result (success/failed/message_id) | HTTP POST, error handling, retry logic |
| **4: Periskope Fetcher** | `periskope_fetcher.py` | Account ID + filters | Message log with delivery status | HTTP GET, JSON parsing, pagination |
| **5: Error Handler** | `error_handler.py` | Exception object | Error log + Claude CLI analysis | Database logging, subprocess, JSON parsing |

---

## API Endpoints (v1.0)

### Send Single Message
```
POST /send
Content-Type: application/json

{
  "phone_number": "+919876543210",
  "message": "Hi {{first_name}}, this is a test from {{company}}",
  "template_variables": {
    "first_name": "Rohan",
    "company": "Candesis"
  }
}

Response:
{
  "status": "success",
  "message_id": "msg_123abc",
  "phone_number": "+919876543210",
  "sent_at": "2026-01-20T10:30:00Z"
}
```

### Send Batch (CSV)
```
POST /batch
Content-Type: multipart/form-data

File: contacts.csv
Format:
  phone_number,first_name,company
  +919876543210,Rohan,Candesis
  +919123456789,Sonia,Gardner

Response:
{
  "batch_id": "batch_xyz",
  "total_contacts": 2,
  "sent": 2,
  "failed": 0,
  "results": [...]
}
```

### Get Message Logs (v2)
```
GET /fetch?account_id=acc_123&limit=50&offset=0

Response:
{
  "messages": [
    {
      "message_id": "msg_123",
      "phone_number": "+919876543210",
      "text": "Hi Rohan...",
      "status": "delivered",
      "sent_at": "2026-01-20T10:30:00Z",
      "delivered_at": "2026-01-20T10:31:00Z"
    }
  ],
  "total": 1000,
  "limit": 50,
  "offset": 0
}
```

### Health Check
```
GET /health

Response:
{
  "status": "ok",
  "version": "1.0",
  "periskope_connected": true
}
```

---

## Configuration

**File: `.env`** (copy from `.env.example`)

```env
# Periskope Credentials
PERISKOPE_API_KEY=pk_live_xxxxxxxxxxxx
PERISKOPE_ACCOUNT_ID=acc_xxxxxxxxxxxx
PERISKOPE_WORKSPACE_ID=ws_xxxxxxxxxxxx

# API Settings
API_ENV=development                # development | production
API_SECRET_KEY=your_secret_key_min_32_chars
API_PORT=8000

# Claude CLI (optional, for error analysis)
CLAUDE_CLI_ENABLED=false
CLAUDE_CLI_TIMEOUT=30

# Logging
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR

# Database
DATABASE_URL=./data/messages.db

# Rate Limiting
MAX_BATCH_SIZE=500                 # Max contacts per batch upload
MAX_REQUESTS_PER_MINUTE=60
```

---

## Usage Examples

### Example 1: Send Single Message
```python
import requests

response = requests.post("http://localhost:8000/send", json={
    "phone_number": "+919876543210",
    "message": "Hi {{first_name}}, {{company}} might benefit from our service!",
    "template_variables": {
        "first_name": "Rohan",
        "company": "Candesis"
    }
})

print(response.json())
# {
#   "status": "success",
#   "message_id": "msg_abc123",
#   "sent_at": "2026-01-20T10:30:00Z"
# }
```

### Example 2: Send Batch from CSV
```bash
curl -X POST http://localhost:8000/batch \
  -F "file=@contacts.csv"
```

### Example 3: Fetch Sent Messages (v2)
```python
response = requests.get("http://localhost:8000/fetch", params={
    "account_id": "acc_xxx",
    "limit": 50,
    "offset": 0
})

print(response.json()["messages"])
```

---

## Key Features

✅ **Modular Agents** — Each agent has one job, easy to test and extend  
✅ **Error Handling** — Comprehensive try-catch with logging and Claude CLI fallback  
✅ **Template Engine** — Send personalized messages with `{{variable}}` substitution  
✅ **Batch Processing** — Upload CSV, send to 500+ contacts  
✅ **Logging** — Structured logs, database audit trail  
✅ **Mock Testing** — Full test suite with mocked Periskope API  
✅ **Production-Ready** — FastAPI with async, proper error codes, validation  

---

## Periskope API Integration

> **IMPORTANT:** Update these once you have the actual Periskope API docs:

**Files to update:**
- `config/constants.py` — Replace placeholder endpoint URLs
- `agents/periskope_sender.py` — Update request/response parsing
- `agents/periskope_fetcher.py` — Update fetch endpoint and pagination logic

**Placeholder endpoints** (to be replaced):
```python
# In config/constants.py
PERISKOPE_BASE_URL = "https://api.periskope.app/v1"  # UPDATE
PERISKOPE_SEND_ENDPOINT = "/messages/send"           # UPDATE
PERISKOPE_FETCH_ENDPOINT = "/messages/history"       # UPDATE
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_message_builder.py -v

# Run with coverage
pytest tests/ --cov=agents --cov-report=html
```

---

## Deployment

### Local Development
```bash
uvicorn main:app --reload --port 8000
```

### Production (Render.com, Vercel, etc.)
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set env vars in your hosting platform's dashboard.

---

## Roadmap (v2.0+)

- [ ] Fetch sent messages endpoint
- [ ] Delivery status tracking & webhooks
- [ ] Facebook API integration
- [ ] Message templates library (UI)
- [ ] Campaign analytics dashboard
- [ ] Retry scheduling
- [ ] Rate limiting & quotas
- [ ] Multi-account support
- [ ] Docker image

---

## Support

For issues or questions:
1. Check `tests/` for examples
2. Review agent docstrings
3. Check error logs in `./data/messages.db`
4. Enable DEBUG logging in `.env`

---

**Built with ❤️ for Ken Research**  
Version 1.0 | Last updated: Jan 2026
