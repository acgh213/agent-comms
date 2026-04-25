"""Base agent definition class."""


class AgentDef:
    """Static definition of an agent's identity and capabilities."""

    def __init__(
        self,
        id,
        name,
        role,
        personality="",
        capabilities=None,
        avatar_color="#888888",
    ):
        self.id = id
        self.name = name
        self.role = role
        self.personality = personality
        self.capabilities = capabilities or []
        self.avatar_color = avatar_color

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "capabilities": self.capabilities,
            "avatar_color": self.avatar_color,
        }

    def __eq__(self, other):
        if not isinstance(other, AgentDef):
            return NotImplemented
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return (
            f"<AgentDef {self.id}: {self.name} ({self.role})>"
        )
