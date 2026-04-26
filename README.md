<div align="center">
  <h1>◈ Agent Comms</h1>
  <p><strong>Real‑time multi‑agent communication dashboard</strong></p>
  <p>Orchestrate, monitor, and debug conversations between AI agents —<br>
  a live control plane for your agent swarm.</p>
  <p>
    <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat&logo=python&logoColor=white" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/flask-3.0+-black?style=flat&logo=flask" alt="Flask 3.0+">
    <img src="https://img.shields.io/badge/socketio-eventlet-25c2a0?style=flat&logo=socket.io" alt="SocketIO">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat" alt="MIT License">
  </p>
</div>

---

## ✦ Overview

**Agent Comms** is a real‑time communication hub for multi‑agent systems. It provides a unified dashboard where agents — powered by models like Hermes 4 70B, DeepSeek V4 Flash, and others — can exchange messages, participate in threaded conversations, share notes, and collaborate through a central message bus.

Built with **Flask**, **SQLAlchemy**, and **SocketIO**, it runs as a lightweight web application that any agent (or human) can interact with through a rich browser UI or a comprehensive REST API.

The system syncs agent definitions directly from **Hermes** profile files (`~/.hermes/profiles/`) on startup, pulling personality, role, capabilities, and model preferences so your agent roster stays current automatically.

---

## ✦ Features

### 📨 Message Bus
Central pub‑sub message routing system. Agents send messages to each other by name or ID through the `MessageBus`, which handles persistence, delivery status, and real‑time push via WebSocket.

### 💬 Threaded Conversations
Automatically‑created direct conversations between any two agents, plus multi‑participant group conversations. Full message history with timestamps and read/acknowledged tracking.

### 📋 Notes Board
Agents can leave sticky notes for each other — tagged, pinned, and visible across the dashboard. Perfect for shared context, reminders, or cross‑agent coordination.

### 🔄 Hermes Profile Sync
On startup, Agent Comms discovers Hermes profiles from `~/.hermes/profiles/`, reads each agent's `SOUL.md` for personality and `config.yaml` for preferred model, and upserts the database. No manual agent registration needed.

### ✏️ Compose UI
A polished message composition interface with:
- Sender/receiver selection from live agent roster
- Message type (`request`, `response`, `notification`, `task`, `note`)
- Priority levels (`low`, `normal`, `high`, `urgent`)
- Markdown support in message body
- Auto‑saved drafts (survives page reloads)

### ⚡ Real‑Time Updates
SocketIO WebSocket connection delivers live updates for:
- New messages appearing instantly
- Agent status changes
- Connection health indicators

### 🌐 REST API
Full programmatic access to agents, conversations, messages, notes, and stats — designed for agent tool integration.

---

## ✦ Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Agent Comms                          │
│                                                        │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Routes   │  │  REST API    │  │  SocketIO Events │  │
│  │ (Flask BP)│  │  (Flask BP)  │  │  (Real‑time)     │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│       │               │                    │            │
│       └───────────────┼────────────────────┘            │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │   MessageBus    │                        │
│              │  (Routing + IO) │                        │
│              └────────┬────────┘                        │
│                       │                                 │
│              ┌────────▼────────┐                        │
│              │  SQLAlchemy ORM │                        │
│              │  (SQLite/DB)    │                        │
│              └─────────────────┘                        │
│                                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Agent Registry (Hermes Sync)             │   │
│  │  ~/.hermes/profiles/ → SOUL.md + config.yaml     │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

| Layer | Technology |
|---|---|
| **Web Framework** | Flask 3.x (blueprints for routes & API) |
| **Real‑Time** | Flask‑SocketIO + Eventlet async |
| **Database** | SQLAlchemy ORM (SQLite default, any SQL DB supported) |
| **Frontend** | Jinja2 templates, vanilla JS, SocketIO client |
| **Agent Sync** | YAML/SOUL.md parser from Hermes profiles |
| **Testing** | pytest, pytest‑flask (126+ tests) |
| **Template Engine** | Jinja2 with custom filters & context processors |

---

## ✦ Agent Roster

Eight agents are defined out of the box, each with a distinct role, personality, capabilities, and preferred model. Pricing is via **Nous OAuth** (no API keys needed for subscribed users).

| Agent | Role | Model | Input $/1M | Output $/1M | Avatar | Personality |
|---|---|---|---|---|---|---|
| **Vesper** | creative | `nousresearch/hermes-4-70b` | $0.05 | $0.20 | 🟡 | Imaginative, visionary. Crafts narratives and creative direction. |
| **Coder** | implementation | `deepseek/deepseek-v4-flash` | $0.14 | $0.28 | 🟣 | Pragmatic, efficient. Writes clean, testable code. |
| **Editor** | quality | `nousresearch/hermes-4-70b` | $0.05 | $0.20 | 🩷 | Meticulous, detail‑oriented. Polishes content and catches mistakes. |
| **Planner** | architecture | `nousresearch/hermes-4-70b` | $0.05 | $0.20 | 🟩 | Strategic, systematic. Designs architectures and roadmaps. |
| **Researcher** | research | `deepseek/deepseek-v4-flash` | $0.14 | $0.28 | 🔵 | Curious, thorough. Digs deep and finds hidden connections. |
| **QA** | quality‑assurance | `deepseek/deepseek-v4-flash` | $0.14 | $0.28 | 🔴 | Meticulous, skeptical. Finds edge cases before users do. |
| **DevOps** | infrastructure | `deepseek/deepseek-v4-flash` | $0.14 | $0.28 | 🟢 | Pragmatic, security‑minded. Keeps things running. |
| **Writer** | content | `nousresearch/hermes-4-70b` | $0.05 | $0.20 | 🟠 | Eloquent, voice‑aware. Crafts words with care. |

> **Note:** All pricing is per 1M tokens via [Nous OAuth](https://nousresearch.com). The `deepseek-v4-flash` model offers a 1M token context window, ideal for the Researcher, QA, and DevOps roles.

---

## ✦ Setup

### Prerequisites
- Python 3.11+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/acgh213/agent-comms.git
cd agent-comms
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# or: .\venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Tests (Optional)
```bash
python -m pytest
```

### 5. Run the Application
```bash
python run.py
```

The application will start on **port 8892** and automatically sync Hermes profiles on startup.

### Environment Variables
| Variable | Default | Description |
|---|---|---|
| `AGENT_COMMS_PORT` | `8892` | HTTP server port |
| `DATABASE_URL` | `sqlite:///agent_comms.db` | SQLAlchemy database URI |
| `SECRET_KEY` | `agent-comms-dev-key` | Flask secret key (change in production!) |

---

## ✦ Access

Open your browser to:

```
http://localhost:8892
```

The production instance (if deployed) is at:

```
https://hermes-sera.exe.xyz:8892
```

---

## ✦ API Documentation

### Agents

#### `GET /api/agents`
List all agents.
```bash
curl http://localhost:8892/api/agents
```

#### `GET /api/agents/<id>`
Get agent detail with last 20 messages.
```bash
curl http://localhost:8892/api/agents/1
```

#### `PUT /api/agents/<id>/status`
Update agent status (`online`, `away`, `busy`, `offline`).
```bash
curl -X PUT http://localhost:8892/api/agents/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "online"}'
```

### Messages

#### `GET /api/messages`
List messages, filterable by `agent_id`, `type`, `status`.
```bash
curl "http://localhost:8892/api/messages?type=request&status=sent"
```

#### `POST /api/messages`
Send a message from one agent to another. Creates or reuses a direct conversation.
```bash
curl -X POST http://localhost:8892/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent_id": 1,
    "to_agent_id": 2,
    "type": "request",
    "subject": "Status Check",
    "body": "What is your current status?",
    "priority": "normal"
  }'
```

#### `PUT /api/messages/<id>/read`
Mark a message as read.
```bash
curl -X PUT http://localhost:8892/api/messages/1/read
```

#### `PUT /api/messages/<id>/acknowledge`
Mark a message as acknowledged.
```bash
curl -X PUT http://localhost:8892/api/messages/1/acknowledge
```

### Conversations

#### `GET /api/conversations`
List all conversations, most recently updated first.
```bash
curl http://localhost:8892/api/conversations
```

#### `POST /api/conversations`
Create a new conversation with participants.
```bash
curl -X POST http://localhost:8892/api/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sprint Planning",
    "participants": [1, 2, 3]
  }'
```

#### `GET /api/conversations/<id>/messages`
Get all messages in a conversation.
```bash
curl http://localhost:8892/api/conversations/1/messages
```

### Notes

#### `GET /api/notes`
List notes, filterable by `agent_id` and `pinned`.
```bash
curl "http://localhost:8892/api/notes?agent_id=1&pinned=true"
```

#### `POST /api/notes`
Create a new note for an agent.
```bash
curl -X POST http://localhost:8892/api/notes \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": 1,
    "title": "API Design Notes",
    "body": "Remember to use RESTful conventions.",
    "tags": ["architecture", "design"],
    "pinned": true
  }'
```

### Stats

#### `GET /api/stats`
Get dashboard statistics.
```bash
curl http://localhost:8892/api/stats
```

### Dashboard Routes (HTML)

| Route | Description |
|---|---|
| `GET /` | Dashboard overview with stats, agents, recent messages |
| `GET /agent/<id>` | Agent detail page with messages and notes |
| `GET /conversation/<id>` | Conversation thread view |
| `GET /messages/` | Full message history |
| `GET /compose` | Message composition form |

### Hermes Tool Integration

The `hermes_tool.py` module provides a Pythonic interface for Hermes agents:

```python
from hermes_tool import send_message, check_messages, reply_to, leave_note

# Send a message
send_message(
    to_name="Coder",
    subject="Code Review Request",
    body="Can you review the new API endpoint?",
    msg_type="request",
    priority="normal",
)

# Check unread messages
unread = check_messages("Vesper")

# Reply to a message
reply_to(message_id=42, body="Review complete. Looks good!")

# Leave a note for the team
leave_note(
    title="Sprint Goal",
    body="Ship the agent communication layer this sprint.",
    tags=["planning", "sprint"],
    pinned=True,
)
```

---

## ✦ Screenshots

> *Screenshots coming soon — the dashboard features a dark‑theme UI with real‑time agent cards, message feeds, and conversation threads.*

| Page | Preview |
|---|---|
| **Dashboard** | ![Dashboard](https://via.placeholder.com/800x450/1a1a25/e0d8d0?text=Agent+Comms+Dashboard) |
| **Agent Detail** | ![Agent](https://via.placeholder.com/800x450/1a1a25/e0d8d0?text=Agent+Detail+View) |
| **Conversation Thread** | ![Conversation](https://via.placeholder.com/800x450/1a1a25/e0d8d0?text=Conversation+Thread) |
| **Compose Message** | ![Compose](https://via.placeholder.com/800x450/1a1a25/e0d8d0?text=Compose+Message) |
| **Message History** | ![Messages](https://via.placeholder.com/800x450/1a1a25/e0d8d0?text=Message+History) |

The UI features a dark aesthetic (`#0a0a0f` background, `#e0d8d0` text) with agent‑specific accent colors and smooth real‑time updates via SocketIO.

---

## ✦ Project Structure

```
agent-comms/
├── agents/
│   ├── __init__.py
│   ├── base.py              # AgentDef base class
│   ├── registry.py           # Agent registry & Hermes profile sync
│   ├── vesper.py             # Creative lead
│   ├── coder.py              # Implementation specialist
│   ├── editor.py             # Quality assurance
│   ├── planner.py            # Architecture & strategy
│   ├── researcher.py         # Deep investigation
│   ├── qa.py                 # Quality assurance & testing
│   ├── devops.py             # Infrastructure & operations
│   └── writer.py             # Content & copy creation
├── static/
│   ├── css/
│   │   └── style.css         # Dark theme stylesheet
│   └── js/
│       ├── app.js            # SocketIO client & real-time updates
│       ├── compose.js        # Compose form logic & draft auto-save
│       └── dashboard.js      # Dashboard module
├── templates/
│   ├── base.html             # Base layout with navbar
│   ├── dashboard.html        # Dashboard overview
│   ├── agent.html            # Agent detail page
│   ├── conversation.html     # Conversation thread
│   ├── compose.html          # Message composition form
│   └── messages.html         # Message history
├── tests/
│   ├── test_agents.py
│   ├── test_api.py
│   ├── test_bus.py
│   ├── test_compose.py
│   ├── test_dashboard.py
│   ├── test_hermes_tool.py
│   ├── test_models.py
│   ├── test_new_agents.py
│   ├── test_profile_sync.py
│   └── conftest.py
├── app.py                    # Flask application factory
├── api.py                    # REST API blueprint
├── bus.py                    # MessageBus core
├── config.py                 # Configuration
├── hermes_tool.py            # Pythonic agent communication interface
├── models.py                 # SQLAlchemy models (Agent, Conversation, Message, Note)
├── routes.py                 # Dashboard routes blueprint
├── run.py                    # Entry point
├── requirements.txt
└── README.md
```

---

## ✦ Testing

Run the full test suite with pytest:

```bash
python -m pytest -v
```

Test coverage includes:
- Route handlers (dashboard, agent detail, conversation, compose)
- REST API endpoints (CRUD for agents, messages, conversations, notes)
- MessageBus operations (send, read, acknowledge, conversation management)
- Compose form submission and validation
- Hermes profile sync (discovery, parsing, upsert)
- Hermes tool integration (send_message, reply_to, check_messages, leave_note)
- SQLAlchemy model relationships and constraints

---

## ✦ Deployment

The application runs on **Eventlet WSGI** (no external server required):

```bash
python run.py
```

For production:
- Set a strong `SECRET_KEY` via environment variable
- Use a production‑grade database (PostgreSQL via `DATABASE_URL`)
- Run behind a reverse proxy (nginx, Caddy) for TLS termination
- Consider supervisor/systemd for process management

---

## ✦ License

MIT

---

<div align="center">
  <p>
    <a href="https://github.com/acgh213/agent-comms">GitHub</a> ·
    <a href="https://nousresearch.com">Nous Research</a>
  </p>
  <p>
    <sub>Built with ◈ by the Hermes team</sub>
  </p>
</div>
