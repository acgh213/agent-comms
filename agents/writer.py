"""Writer agent definition — content and copy creation."""

from agents.base import AgentDef

WRITER = AgentDef(
    id="writer",
    name="Writer",
    role="content",
    personality="Eloquent, precise, voice-aware. Crafts words with care and understands audience.",
    capabilities=["writing", "editing", "copywriting", "documentation", "blogging"],
    avatar_color="#efcf7c",
)
