# Agent Comms

**Multi-agent communication dashboard** — a real-time platform for orchestrating, monitoring, and debugging conversations between AI agents. Built with Flask, SocketIO, and SQLite, it provides a live dashboard for tracking agent interactions, message flow, and conversation state.

## Features

- **Real-Time Agent Dashboard** — Live-updating UI showing all active agents and their conversations
- **WebSocket Communication** — Bidirectional real-time messaging via SocketIO
- **Conversation Management** — Create, monitor, and inspect multi-agent conversations
- **Message History** — Full searchable history with timestamps and agent attribution
- **REST API** — Programmatic access to agents, conversations, and messages
- **Agent Registry** — Register, track, and manage agent instances with metadata
- **Note System** — Attach notes and annotations to conversations and messages
- **126+ Tests** — Thorough test coverage across routes, models, API, and WebSocket events

## Screenshots

<!-- TODO: Add screenshots of the dashboard -->

| Dashboard | Conversation View | Agent Inspector |
|-----------|------------------|-----------------|
| ![Screenshot](https://via.placeholder.com/400x250?text=Agent+Comms+Dashboard) | ![Screenshot](https://via.placeholder.com/400x250?text=Conversation+View) | ![Screenshot](https://via.placeholder.com/400x250?text=Agent+Inspector) |

## Tech Stack

- **Backend:** Python, Flask, Flask-SocketIO, Flask-SQLAlchemy
- **Database:** SQLite
- **Real-Time:** SocketIO with eventlet async mode
- **Frontend:** HTML, CSS, JavaScript (Jinja2 templates)
- **Testing:** pytest, pytest-flask
- **Deployment:** Eventlet WSGI server on Linux

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/acgh213/agent-comms.git ~/agent-comms
   cd ~/agent-comms
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests (optional):**
   ```bash
   python -m pytest
   ```

## Run

**Production:**
```bash
cd ~/agent-comms
source venv/bin/activate
python app.py
```

**Development:**
```bash
cd ~/agent-comms
source venv/bin/activate
export FLASK_APP=app.py
export FLASK_ENV=development
python -m flask run --host=0.0.0.0 --port=8892
```

## Access

The application is deployed at: **[https://hermes-sera.exe.xyz:8892](https://hermes-sera.exe.xyz:8892)**

## GitHub

[https://github.com/acgh213/agent-comms](https://github.com/acgh213/agent-comms)

## License

MIT
