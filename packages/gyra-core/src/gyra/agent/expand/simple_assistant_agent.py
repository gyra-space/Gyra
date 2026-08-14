"""Simple Assistant Agent."""

import logging

from ..core.action.blank_action import BlankAction
from ..core.base_agent import ConversableAgent
from ..core.profile import DynConfig, ProfileConfig

logger = logging.getLogger(__name__)


class SimpleAssistantAgent(ConversableAgent):
    """Simple Assistant Agent."""

    profile: ProfileConfig = ProfileConfig(
        name=DynConfig(
            "Tom",
            category="agent",
            key="gyra_agent_expand_simple_assistant_agent_profile_name",
        ),
        role=DynConfig(
            "AI Assistant",
            category="agent",
            key="gyra_agent_expand_simple_assistant_agent_profile_role",
        ),
        goal=DynConfig(
            "Understand user questions and give professional answer",
            category="agent",
            key="gyra_agent_expand_simple_assistant_agent_profile_goal",
        ),
        constraints=DynConfig(
            [
                "Please make sure your answer is clear, logical, "
                "friendly, and human-readable."
            ],
            category="agent",
            key="gyra_agent_expand_simple_assistant_agent_profile_constraints",
        ),
        desc=DynConfig(
            "I am a universal simple AI assistant.",
            category="agent",
            key="gyra_agent_expand_summary_assistant_agent_profile_desc",
        ),
    )

    def __init__(self, **kwargs):
        """Create a new SummaryAssistantAgent instance."""
        super().__init__(**kwargs)
        self._init_actions([BlankAction])

