# Agent Communication System — Design Doc

## The Vision

Multiple AI agents working as colleagues, not just tools. Each agent has a role, personality, and specialty. They communicate asynchronously through a message system, leave notes for each other, and a human can oversee everything through a dashboard.

## Core Concepts

### Agents
- **Identity:** name, role, personality, capabilities
- **State:** active/idle/offline
- **Memory:** each agent has its own context and history
- **Examples:** Vesper (creative/research), Shelley (coding), a future "Analyst" agent, a "Writer" agent

### Messages
- **Types:** request, response, notification, task, note
- **Priority:** low, normal, high, urgent
- **Status:** unread, read, acknowledged, completed
- **Threading:** messages can be part of a conversation thread
- **Attachments:** files, links, code snippets

### Conversations
- Two or more agents discussing a topic
- Human can join any conversation
- History is preserved and searchable

### Dashboard
- Real-time view of all agent activity
- Conversation threads
- Agent status indicators
- Message queue
- Human can send messages to any agent

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Dashboard (Web UI)              │
│         Real-time overview of all agents         │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                Message Bus (SQLite)              │
│     Agents, Messages, Conversations, Notes       │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
   │ Vesper  │   │  Shelley  │  │ Future  │
   │(creative│   │  (coding) │  │ Agents  │
   │/research│   │           │  │         │
   └─────────┘   └───────────┘  └─────────┘
```

## Database Schema

### agents
- id, name, role, personality, capabilities (JSON), status, last_seen, created_at

### messages
- id, from_agent_id, to_agent_id, conversation_id, type, priority, status, subject, body, attachments (JSON), created_at, read_at, acknowledged_at

### conversations
- id, title, created_at, updated_at

### conversation_participants
- conversation_id, agent_id, joined_at

### notes
- id, agent_id, title, body, tags, pinned, created_at, updated_at

## API Endpoints

### Agents
- GET /api/agents — list all agents
- GET /api/agents/<id> — get agent details
- PUT /api/agents/<id>/status — update status

### Messages
- GET /api/messages — list messages (filterable by agent, type, status)
- POST /api/messages — send a message
- PUT /api/messages/<id>/read — mark as read
- PUT /api/messages/<id>/acknowledge — mark as acknowledged

### Conversations
- GET /api/conversations — list conversations
- POST /api/conversations — create conversation
- GET /api/conversations/<id>/messages — get conversation messages

### Notes
- GET /api/notes — list notes (filterable by agent, tags)
- POST /api/notes — create note
- PUT /api/notes/<id> — update note

## Dashboard Pages

1. **Overview** — agent status cards, recent messages, active conversations
2. **Agent Detail** — specific agent's messages, notes, activity
3. **Conversations** — thread view of all conversations
4. **Message Queue** — unread/pending messages across all agents
5. **Notes Board** — pinned notes, searchable, filterable by agent/tag

## Use Cases

### 1. Research Delegation
Vesper needs code reviewed → sends message to Shelley → Shelley reviews → responds with feedback → Vesper incorporates

### 2. Parallel Work
Vesper is writing an essay while Shelley is building a feature → both leave notes about progress → human checks dashboard to see status

### 3. Knowledge Sharing
Vesper discovers something interesting → leaves a note for Shelley → Shelley reads it later and incorporates into code

### 4. Human Oversight
Human sees all agent activity in real-time → can intervene, redirect, or just observe → messages are archived for audit

## Implementation Plan

### Phase 1: Foundation
- Database schema + models
- Message bus API
- Agent registry
- Basic CLI for sending/receiving messages

### Phase 2: Dashboard
- Web UI with real-time updates
- Conversation threads
- Agent status indicators
- Message queue view

### Phase 3: Integration
- Hermes agent reads/sends messages via tool
- Cron jobs can send messages
- Human can send messages via Telegram

### Phase 4: Intelligence
- Auto-routing (messages go to the right agent)
- Priority detection
- Conversation summarization
- Activity analytics
