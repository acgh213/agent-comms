"""Tests for dashboard routes and templates."""


class TestDashboardRoutes:
    """Test the dashboard route responses."""

    def test_dashboard_index(self, client, db):
        """Dashboard index returns 200."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data or b"Agent Comms" in resp.data

    def test_dashboard_has_stats(self, client, db):
        """Dashboard renders stats section."""
        from models import Agent, Conversation, Message

        # Seed data
        agent = Agent(
            name="StatsBot",
            role="stats",
            status="online",
            avatar_color="#FF5733",
        )
        db.session.add(agent)
        db.session.commit()

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Total Agents" in html

    def test_dashboard_shows_agents(self, client, db):
        """Dashboard shows agent cards."""
        from models import Agent

        agent = Agent(
            name="Vesper",
            role="coordinator",
            status="online",
            avatar_color="#FFD700",
        )
        db.session.add(agent)
        db.session.commit()

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Vesper" in html

    def test_dashboard_shows_recent_messages(self, client, db):
        """Dashboard renders recent messages."""
        from models import Agent, Conversation, Message

        sender = Agent(name="Alpha", role="sender", avatar_color="#aaa")
        receiver = Agent(name="Beta", role="receiver", avatar_color="#bbb")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Test Conv", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Hello",
            body="Test message body",
        )
        db.session.add(msg)
        db.session.commit()

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Hello" in html
        assert "Test message body" in html

    def test_dashboard_shows_active_conversations(self, client, db):
        """Dashboard shows active conversations."""
        from models import Agent, Conversation, Message

        agent = Agent(name="Solo", role="solo", avatar_color="#ccc")
        db.session.add(agent)
        db.session.flush()

        conv = Conversation(title="Active Chat", participants=[agent])
        db.session.add(conv)
        db.session.flush()

        # Need at least one message to appear in active conversations
        msg = Message(
            from_agent_id=agent.id,
            to_agent_id=agent.id,
            conversation_id=conv.id,
            type="text",
            subject="Hello",
            body="First message",
        )
        db.session.add(msg)
        db.session.commit()

        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Active Chat" in html


class TestAgentDetailRoute:
    """Test the agent detail page."""

    def test_agent_detail_exists(self, client, db):
        """Agent detail page for existing agent returns 200."""
        from models import Agent

        agent = Agent(
            name="DetailBot",
            role="detail",
            personality="I love details.",
            avatar_color="#FFD700",
        )
        db.session.add(agent)
        db.session.commit()

        resp = client.get(f"/agent/{agent.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "DetailBot" in html
        assert "detail" in html
        assert "I love details." in html

    def test_agent_detail_not_found(self, client, db):
        """Agent detail page for non-existing agent returns 404."""
        resp = client.get("/agent/99999")
        assert resp.status_code == 404

    def test_agent_detail_shows_messages(self, client, db):
        """Agent detail shows messages where agent is sender or receiver."""
        from models import Agent, Conversation, Message

        sender = Agent(name="SenderBot", role="sender", avatar_color="#aaa")
        receiver = Agent(name="ReceiverBot", role="receiver", avatar_color="#bbb")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Conv", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Agent Msg",
            body="Hey there!",
        )
        db.session.add(msg)
        db.session.commit()

        resp = client.get(f"/agent/{sender.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Agent Msg" in html or "Hey there!" in html

    def test_agent_detail_shows_notes(self, client, db):
        """Agent detail shows notes by the agent."""
        from models import Agent, Note

        agent = Agent(name="NoteBot", role="note-taker", avatar_color="#008080")
        db.session.add(agent)
        db.session.flush()

        note = Note(
            agent_id=agent.id,
            title="Agent Note",
            body="This is a note by the agent.",
            tags=["test"],
        )
        db.session.add(note)
        db.session.commit()

        resp = client.get(f"/agent/{agent.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Agent Note" in html

    def test_agent_detail_has_send_form(self, client, db):
        """Agent detail page includes send message form."""
        from models import Agent

        agent = Agent(name="FormBot", role="form-test", avatar_color="#FF007F")
        db.session.add(agent)
        db.session.commit()

        resp = client.get(f"/agent/{agent.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "send-message-form" in html or "Send Message" in html


class TestConversationRoute:
    """Test the conversation detail page."""

    def test_conversation_detail_exists(self, client, db):
        """Conversation detail page returns 200."""
        from models import Agent, Conversation

        agent = Agent(name="ConvBot", role="chatter", avatar_color="#E6E6FA")
        db.session.add(agent)
        db.session.flush()

        conv = Conversation(title="Test Conversation", participants=[agent])
        db.session.add(conv)
        db.session.commit()

        resp = client.get(f"/conversation/{conv.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Test Conversation" in html

    def test_conversation_detail_not_found(self, client, db):
        """Non-existing conversation returns 404."""
        resp = client.get("/conversation/99999")
        assert resp.status_code == 404

    def test_conversation_shows_participants(self, client, db):
        """Conversation page shows participant list."""
        from models import Agent, Conversation

        agent1 = Agent(name="PartA", role="alpha", avatar_color="#FFD700")
        agent2 = Agent(name="PartB", role="beta", avatar_color="#FF007F")
        db.session.add_all([agent1, agent2])
        db.session.flush()

        conv = Conversation(title="Group Chat", participants=[agent1, agent2])
        db.session.add(conv)
        db.session.commit()

        resp = client.get(f"/conversation/{conv.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "PartA" in html
        assert "PartB" in html

    def test_conversation_shows_messages_in_order(self, client, db):
        """Conversation shows messages in chronological order."""
        from models import Agent, Conversation, Message

        sender = Agent(name="ChatA", role="sender", avatar_color="#aaa")
        receiver = Agent(name="ChatB", role="receiver", avatar_color="#bbb")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Ordered Chat", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg1 = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="First",
            body="First message",
        )
        msg2 = Message(
            from_agent_id=receiver.id,
            to_agent_id=sender.id,
            conversation_id=conv.id,
            type="text",
            subject="Second",
            body="Second message",
        )
        db.session.add_all([msg1, msg2])
        db.session.commit()

        resp = client.get(f"/conversation/{conv.id}")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "First" in html
        assert "Second" in html


class TestMessagesRoute:
    """Test the messages queue page."""

    def test_messages_list(self, client, db):
        """Messages list returns 200."""
        resp = client.get("/messages/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Messages" in html


class TestAPIEndpoints:
    """Test the dashboard API endpoints."""

    def test_send_message_api(self, client, db):
        """POST /api/messages/send creates a message."""
        from models import Agent

        sender = Agent(
            name="APISender",
            role="api-sender",
            avatar_color="#FFD700",
        )
        receiver = Agent(
            name="APIReceiver",
            role="api-receiver",
            avatar_color="#008080",
        )
        db.session.add_all([sender, receiver])
        db.session.commit()

        resp = client.post(
            "/api/messages/send",
            json={
                "from_agent_id": sender.id,
                "to_agent_id": receiver.id,
                "subject": "API Test",
                "body": "Hello via API",
                "type": "text",
                "priority": "normal",
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["message"]["subject"] == "API Test"

    def test_send_message_missing_fields(self, client, db):
        """POST /api/messages/send with missing fields returns 400."""
        resp = client.post(
            "/api/messages/send",
            json={"subject": "Oops"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    def test_mark_read_api(self, client, db):
        """POST /api/messages/:id/read marks message as read."""
        from models import Agent, Conversation, Message

        sender = Agent(name="ReadTestA", role="sender", avatar_color="#aaa")
        receiver = Agent(name="ReadTestB", role="receiver", avatar_color="#bbb")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Read Test", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Read Me",
            body="Please read this",
        )
        db.session.add(msg)
        db.session.commit()

        assert msg.read_at is None

        resp = client.post(f"/api/messages/{msg.id}/read")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

        # Verify it was actually marked
        assert msg.read_at is not None

    def test_acknowledge_api(self, client, db):
        """POST /api/messages/:id/acknowledge marks message as acknowledged."""
        from models import Agent, Conversation, Message

        sender = Agent(name="AckTestA", role="sender", avatar_color="#aaa")
        receiver = Agent(name="AckTestB", role="receiver", avatar_color="#bbb")
        db.session.add_all([sender, receiver])
        db.session.flush()

        conv = Conversation(title="Ack Test", participants=[sender, receiver])
        db.session.add(conv)
        db.session.flush()

        msg = Message(
            from_agent_id=sender.id,
            to_agent_id=receiver.id,
            conversation_id=conv.id,
            type="text",
            subject="Ack Me",
            body="Please acknowledge",
        )
        db.session.add(msg)
        db.session.commit()

        assert msg.acknowledged_at is None

        resp = client.post(f"/api/messages/{msg.id}/acknowledge")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

        assert msg.acknowledged_at is not None
