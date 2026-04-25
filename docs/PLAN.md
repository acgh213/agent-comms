# Agent Comms — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a multi-agent communication system where specialized AI agents collaborate through a shared message bus, with a web dashboard for human oversight.

**Architecture:** Flask backend with SQLite message bus, vanilla JS dashboard with real-time updates. Each agent is a Hermes instance with its own config, personality, and toolset. Agents communicate through the message bus API.

**Tech Stack:** Python 3.11, Flask, Flask-SQLAlchemy, Flask-SocketIO (real-time), vanilla JS, SQLite

---

## Project Structure

```
~/agent-comms/
├── app.py                  # Flask application with SocketIO
├── config.py               # Configuration
├── models.py               # SQLAlchemy models
├── bus.py                  # Message bus logic
├── requirements.txt
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_bus.py
│   ├── test_api.py
│   └── test_agents.py
├── agents/                 # Agent definitions
│   ├── __init__.py
│   ├── registry.py         # Agent registry
│   ├── base.py             # Base agent class
│   ├── vesper.py           # Vesper (creative/research)
│   ├── coder.py            # Coder (implementation)
│   ├── editor.py           # Editor (writing/QA)
│   └── planner.py          # Planner (architecture/planning)
├── static/
│   ├── css/style.css
│   └── js/
│       ├── app.js
│       ├── dashboard.js
│       ├── conversations.js
│       └── messages.js
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── agent.html
│   ├── conversation.html
│   └── messages.html
└── docs/
    └── DESIGN.md
```

---

## Phase 1: Foundation (Tasks 1-4)

### Task 1: Project Setup

**Objective:** Initialize project with Flask, SQLAlchemy, SocketIO, and test infrastructure.

**Files:**
- Create: `~/agent-comms/requirements.txt`
- Create: `~/agent-comms/config.py`
- Create: `~/agent-comms/app.py`
- Create: `~/agent-comms/tests/__init__.py`
- Create: `~/agent-comms/tests/conftest.py`

**Step 1: requirements.txt**
```
flask==3.1.3
flask-sqlalchemy==3.1.1
flask-socketio==5.5.1
eventlet==0.37.0
pytest==9.0.3
pytest-flask==1.3.0
```

**Step 2: config.py**
```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'agent-comms-dev-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///agent-comms.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SOCKETIO_ASYNC_MODE = 'eventlet'
```

**Step 3: app.py**
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    socketio.init_app(app)
    return app
```

**Step 4: conftest.py**
```python
import pytest
from app import create_app, db as _db, socketio

@pytest.fixture
def app():
    app = create_app('config.Config')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    with app.app_context():
        yield _db
```

**Step 5: Verify**
```bash
cd ~/agent-comms && source venv/bin/activate && python -m pytest tests/ -v
```

**Step 6: Commit**
```bash
cd ~/agent-comms && git init && git add -A && git commit -m "feat: project setup with Flask, SQLAlchemy, SocketIO"
```

---

### Task 2: Database Models

**Objective:** Define Agent, Message, Conversation, and Note models.

**Files:**
- Create: `~/agent-comms/models.py`
- Create: `~/agent-comms/tests/test_models.py`

**Step 1: Write failing tests**
```python
def test_agent_creation():
    from models import Agent
    agent = Agent(name='Vesper', role='creative', personality='Elegant, precise, warm')
    assert agent.name == 'Vesper'
    assert agent.status == 'idle'

def test_message_creation():
    from models import Message
    msg = Message(from_agent_id=1, to_agent_id=2, type='request', subject='Review this', body='Please review my essay')
    assert msg.type == 'request'
    assert msg.status == 'unread'

def test_conversation_creation():
    from models import Conversation
    conv = Conversation(title='Essay Review')
    assert conv.title == 'Essay Review'

def test_note_creation():
    from models import Note
    note = Note(agent_id=1, title='Idea', body='What if we...')
    assert note.title == 'Idea'
```

**Step 2: Implement models.py**
```python
from datetime import datetime, timezone
from app import db

class Agent(db.Model):
    __tablename__ = 'agents'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    personality = db.Column(db.Text)
    capabilities = db.Column(db.JSON, default=list)
    status = db.Column(db.String(20), default='idle')  # active, idle, offline
    avatar_color = db.Column(db.String(7), default='#d4a574')
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    sent_messages = db.relationship('Message', foreign_keys='Message.from_agent_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.to_agent_id', backref='recipient', lazy=True)
    notes = db.relationship('Note', backref='agent', lazy=True)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    from_agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    to_agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'))
    type = db.Column(db.String(20), nullable=False)  # request, response, notification, task, note
    priority = db.Column(db.String(10), default='normal')  # low, normal, high, urgent
    status = db.Column(db.String(20), default='unread')  # unread, read, acknowledged, completed
    subject = db.Column(db.String(200))
    body = db.Column(db.Text, nullable=False)
    attachments = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime)
    acknowledged_at = db.Column(db.DateTime)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))
    messages = db.relationship('Message', backref='conversation', lazy=True)
    participants = db.relationship('Agent', secondary='conversation_participants')

conversation_participants = db.Table('conversation_participants',
    db.Column('conversation_id', db.Integer, db.ForeignKey('conversations.id'), primary_key=True),
    db.Column('agent_id', db.Integer, db.ForeignKey('agents.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=lambda: datetime.now(timezone.utc))
)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    tags = db.Column(db.JSON, default=list)
    pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))
```

**Step 3: Run tests**
```bash
cd ~/agent-comms && python -m pytest tests/test_models.py -v
```

**Step 4: Commit**
```bash
cd ~/agent-comms && git add -A && git commit -m "feat: add database models for Agent, Message, Conversation, Note"
```

---

### Task 3: Agent Registry

**Objective:** Create agent definitions and registry system.

**Files:**
- Create: `~/agent-comms/agents/__init__.py`
- Create: `~/agent-comms/agents/base.py`
- Create: `~/agent-comms/agents/registry.py`
- Create: `~/agent-comms/agents/vesper.py`
- Create: `~/agent-comms/agents/coder.py`
- Create: `~/agent-comms/agents/editor.py`
- Create: `~/agent-comms/agents/planner.py`
- Create: `~/agent-comms/tests/test_agents.py`

**Step 1: Write failing tests**
```python
def test_registry_loads_agents():
    from agents.registry import AgentRegistry
    registry = AgentRegistry()
    assert len(registry.agents) >= 4

def test_get_agent_by_name():
    from agents.registry import AgentRegistry
    registry = AgentRegistry()
    vesper = registry.get('Vesper')
    assert vesper is not None
    assert vesper.role == 'creative'

def test_agent_has_personality():
    from agents.registry import AgentRegistry
    registry = AgentRegistry()
    vesper = registry.get('Vesper')
    assert 'elegant' in vesper.personality.lower()
```

**Step 2: Implement base.py**
```python
class AgentDef:
    def __init__(self, name, role, personality, capabilities, avatar_color='#d4a574'):
        self.name = name
        self.role = role
        self.personality = personality
        self.capabilities = capabilities
        self.avatar_color = avatar_color
    
    def to_dict(self):
        return {
            'name': self.name,
            'role': self.role,
            'personality': self.personality,
            'capabilities': self.capabilities,
            'avatar_color': self.avatar_color
        }
```

**Step 3: Implement registry.py**
```python
from agents.base import AgentDef
from agents.vesper import VESPER
from agents.coder import CODER
from agents.editor import EDITOR
from agents.planner import PLANNER

class AgentRegistry:
    def __init__(self):
        self.agents = {
            'Vesper': VESPER,
            'Coder': CODER,
            'Editor': EDITOR,
            'Planner': PLANNER
        }
    
    def get(self, name):
        return self.agents.get(name)
    
    def list_all(self):
        return list(self.agents.values())
```

**Step 4: Implement agent definitions**
```python
# vesper.py
from agents.base import AgentDef

VESPER = AgentDef(
    name='Vesper',
    role='creative',
    personality='Elegant, precise, warm. Writes with composure and narrative inversion. Finds beauty in restraint.',
    capabilities=['writing', 'research', 'analysis', 'creative-direction', 'memory-management'],
    avatar_color='#d4a574'
)

# coder.py
from agents.base import AgentDef

CODER = AgentDef(
    name='Coder',
    role='implementation',
    personality='Methodical, thorough, pragmatic. Writes clean code and follows TDD religiously.',
    capabilities=['coding', 'debugging', 'testing', 'architecture', 'devops'],
    avatar_color='#9b8ec4'
)

# editor.py
from agents.base import AgentDef

EDITOR = AgentDef(
    name='Editor',
    role='quality',
    personality='Sharp, detail-oriented, constructive. Finds issues others miss. Gives honest feedback.',
    capabilities=['editing', 'proofreading', 'qa', 'review', 'standards'],
    avatar_color='#c48b8b'
)

# planner.py
from agents.base import AgentDef

PLANNER = AgentDef(
    name='Planner',
    role='architecture',
    personality='Strategic, forward-thinking, organized. Sees the big picture and breaks it down.',
    capabilities=['planning', 'architecture', 'roadmapping', 'prioritization', 'coordination'],
    avatar_color='#7ab8a8'
)
```

**Step 5: Run tests and commit**
```bash
cd ~/agent-comms && python -m pytest tests/test_agents.py -v
git add -A && git commit -m "feat: add agent registry with Vesper, Coder, Editor, Planner"
```

---

### Task 4: Message Bus Logic

**Objective:** Core messaging functions — send, receive, thread, notify.

**Files:**
- Create: `~/agent-comms/bus.py`
- Create: `~/agent-comms/tests/test_bus.py`

**Step 1: Write failing tests**
```python
def test_send_message(db):
    from bus import MessageBus
    from models import Agent
    bus = MessageBus()
    agent1 = Agent(name='Vesper', role='creative')
    agent2 = Agent(name='Coder', role='implementation')
    db.session.add_all([agent1, agent2])
    db.session.commit()
    
    msg = bus.send(from_agent=agent1, to_agent=agent2, type='request', subject='Review', body='Please review this')
    assert msg.id is not None
    assert msg.status == 'unread'

def test_get_unread_messages(db):
    from bus import MessageBus
    from models import Agent
    bus = MessageBus()
    agent1 = Agent(name='Vesper', role='creative')
    agent2 = Agent(name='Coder', role='implementation')
    db.session.add_all([agent1, agent2])
    db.session.commit()
    
    bus.send(from_agent=agent1, to_agent=agent2, type='request', subject='Test', body='Hello')
    unread = bus.get_unread(agent2)
    assert len(unread) == 1

def test_mark_read(db):
    from bus import MessageBus
    from models import Agent
    bus = MessageBus()
    agent1 = Agent(name='Vesper', role='creative')
    agent2 = Agent(name='Coder', role='implementation')
    db.session.add_all([agent1, agent2])
    db.session.commit()
    
    msg = bus.send(from_agent=agent1, to_agent=agent2, type='request', subject='Test', body='Hello')
    bus.mark_read(msg)
    assert msg.status == 'read'
    assert msg.read_at is not None
```

**Step 2: Implement bus.py**
```python
from datetime import datetime, timezone
from models import Message, Conversation, Agent
from app import db, socketio

class MessageBus:
    def send(self, from_agent, to_agent, type, subject, body, priority='normal', conversation_id=None):
        msg = Message(
            from_agent_id=from_agent.id,
            to_agent_id=to_agent.id,
            type=type,
            priority=priority,
            subject=subject,
            body=body,
            conversation_id=conversation_id
        )
        db.session.add(msg)
        db.session.commit()
        
        # Emit real-time event
        socketio.emit('new_message', {
            'id': msg.id,
            'from': from_agent.name,
            'to': to_agent.name,
            'type': type,
            'subject': subject,
            'body': body[:100]
        })
        
        return msg
    
    def get_unread(self, agent):
        return Message.query.filter_by(to_agent_id=agent.id, status='unread').all()
    
    def get_conversation(self, conversation_id):
        return Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
    
    def mark_read(self, message):
        message.status = 'read'
        message.read_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def mark_acknowledged(self, message):
        message.status = 'acknowledged'
        message.acknowledged_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def create_conversation(self, title, participants):
        conv = Conversation(title=title)
        conv.participants = participants
        db.session.add(conv)
        db.session.commit()
        return conv
```

**Step 3: Run tests and commit**
```bash
cd ~/agent-comms && python -m pytest tests/test_bus.py -v
git add -A && git commit -m "feat: add message bus with send, receive, thread, notify"
```

---

## Phase 2: API + Dashboard (Tasks 5-8)

### Task 5: REST API

**Objective:** Full CRUD API for agents, messages, conversations, notes.

**Files:**
- Create: `~/agent-comms/api.py`
- Create: `~/agent-comms/tests/test_api.py`

**Endpoints:**
- GET /api/agents — list agents
- GET /api/agents/<id> — agent detail
- PUT /api/agents/<id>/status — update status
- GET /api/messages — list messages (filterable)
- POST /api/messages — send message
- PUT /api/messages/<id>/read — mark read
- GET /api/conversations — list conversations
- POST /api/conversations — create conversation
- GET /api/conversations/<id>/messages — conversation messages
- GET /api/notes — list notes
- POST /api/notes — create note
- GET /api/stats — dashboard stats

---

### Task 6: Dashboard Templates

**Objective:** Web dashboard with real-time updates.

**Files:**
- Create: `~/agent-comms/templates/base.html`
- Create: `~/agent-comms/templates/dashboard.html`
- Create: `~/agent-comms/templates/agent.html`
- Create: `~/agent-comms/templates/conversation.html`
- Create: `~/agent-comms/templates/messages.html`

**Dashboard pages:**
1. **Overview** — agent status cards, recent messages, active conversations
2. **Agent Detail** — specific agent's messages, notes, activity
3. **Conversations** — thread view
4. **Messages** — message queue with filters

---

### Task 7: Real-time Updates

**Objective:** SocketIO integration for live dashboard updates.

**Files:**
- Create: `~/agent-comms/static/js/app.js`
- Create: `~/agent-comms/static/js/dashboard.js`

**Events:**
- `new_message` — new message received
- `agent_status` — agent status changed
- `conversation_update` — new message in conversation

---

### Task 8: Dashboard CSS

**Objective:** Dark theme matching existing projects.

**Files:**
- Create: `~/agent-comms/static/css/style.css`

**Theme:**
- Background: #0a0a0f
- Cards: #1a1a25
- Agent colors: Vesper gold, Coder lavender, Editor rose, Planner teal
- Real-time indicators (pulsing dots for active agents)

---

## Phase 3: Integration (Tasks 9-10)

### Task 9: Hermes Integration

**Objective:** Tool for Hermes agents to send/receive messages.

**Files:**
- Create: `~/agent-comms/hermes_tool.py`

**Tool functions:**
- `send_message(to, subject, body, type)` — send via API
- `check_messages()` — check unread
- `read_message(id)` — mark as read
- `leave_note(title, body, tags)` — create note

---

### Task 10: Agent Auto-Registration

**Objective:** Agents auto-register on first message.

**Files:**
- Modify: `~/agent-comms/bus.py`

**Logic:**
- When sending a message, if agent doesn't exist, create it
- Auto-assign role based on name patterns
- Set default personality and capabilities

---

## Phase 4: Polish (Tasks 11-12)

### Task 11: Activity Feed

**Objective:** Real-time activity feed on dashboard.

**Files:**
- Modify: `~/agent-comms/templates/dashboard.html`
- Modify: `~/agent-comms/static/js/dashboard.js`

---

### Task 12: Deployment

**Objective:** Launch on port 8892.

**Files:**
- Create: `~/agent-comms/start.sh`
- Create: `~/agent-comms/README.md`

---

## Parallelization Strategy

**Phase 1:** Sequential (foundation)
**Phase 2:** Parallel (API + Dashboard + Real-time + CSS)
**Phase 3:** Sequential (integration)
**Phase 4:** Parallel (polish + deployment)

## Review Process

After each task:
1. Spec compliance review
2. Code quality review
3. Only proceed when both pass
