#!/usr/bin/env python3
"""Agent Comms — entry point."""

import os
import sys

PORT = int(os.environ.get("AGENT_COMMS_PORT", 8892))

if __name__ == "__main__":
    from app import create_app, socketio, db

    app = create_app()

    # Sync Hermes profiles into the DB on startup
    with app.app_context():
        from agents.registry import sync_agents
        agents = sync_agents()
        print(f"✓ Synced {len(agents)} agents from Hermes profiles")

    print(f"🚀 Agent Comms starting on port {PORT}")
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
