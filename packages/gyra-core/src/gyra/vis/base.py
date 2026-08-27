"""Base class for vis protocol module."""

import json
import logging
from typing import Any, Dict, Optional, Type

import orjson

from gyra.util.json_utils import serialize

logger = logging.getLogger(__name__)


class Vis:
    """Vis protocol base class."""

    # Class-level registry for vis components
    _registry: Dict[str, "Vis"] = {}

    def __init__(self, **kwargs):
        """
        vis init
        Args:
            **kwargs:
        """

    def render_prompt(self) -> Optional[str]:
        """Return the prompt for the vis protocol."""
        return None

    def sync_generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate the parameters required by the vis protocol.

        Display corresponding content using vis protocol

        Args:
            **kwargs:

        Returns:
        vis protocol text
        """
        return kwargs["content"]

    async def generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate the parameters required by the vis protocol.

        Display corresponding content using vis protocol
        Args:
            **kwargs:

        Returns:
        vis protocol text
        """
        return self.sync_generate_param(**kwargs)

    def sync_display(self, **kwargs) -> Optional[str]:
        """Display the content using the vis protocol."""
        # content = json.dumps(
        #     self.sync_generate_param(**kwargs), default=serialize, ensure_ascii=False
        # )
        content = orjson.dumps(
            self.sync_generate_param(**kwargs), default=serialize
        ).decode()
        return f"```{self.vis_tag()}\n{content}\n```"

    async def display(self, **kwargs) -> Optional[str]:
        """Display the content using the vis protocol."""
        return self.sync_display(**kwargs)

    @classmethod
    def vis_tag(cls) -> str:
        """Return current vis protocol module tag name."""
        return ""

    @classmethod
    def of(cls, vis_type: str) -> Optional["Vis"]:
        """
        Factory method to get a vis component by type.

        Args:
            vis_type: The type of vis component (e.g., 'code', 'text', 'chart')

        Returns:
            Vis instance or None if not found
        """
        # First check the registry
        if vis_type in cls._registry:
            return cls._registry[vis_type]

        # Try to import and register from gyra_ext.vis
        try:
            from gyra_ext.vis.gyra.gyra_vis_manage import VisManager

            vis_manager = VisManager()
            vis_class = vis_manager.get_vis_class(vis_type)
            if vis_class:
                instance = vis_class()
                cls._registry[vis_type] = instance
                return instance
        except ImportError:
            pass

        # Try common vis types by direct import
        vis_map = {
            "code": ("gyra_ext.vis.common.tags.gyra_code", "CodeSpace"),
            "text": ("gyra_ext.vis.gyra.tags.drsk_content", "DrskContent"),
            "thinking": (
                "gyra_ext.vis.common.tags.gyra_thinking",
                "GyraThinking",
            ),
            "plan": ("gyra_ext.vis.common.tags.gyra_plan", "AgentPlan"),
            "todo_list": ("gyra_ext.vis.common.tags.gyra_todo_list", "TodoList"),
            "subagent_board": (
                "gyra_ext.vis.common.tags.gyra_subagent_board",
                "SubagentBoard",
            ),
            "d-attach": ("gyra_ext.vis.common.tags.gyra_attach", "GyraAttach"),
            "d-sql-query": ("gyra_ext.vis.common.tags.gyra_sql_query", "GyraSqlQuery"),
            "d-ecp-search": ("gyra_ext.vis.common.tags.gyra_ecp_search", "GyraEcpSearch"),
            "d-ecp-metric": ("gyra_ext.vis.common.tags.gyra_ecp_metric", "GyraEcpMetric"),
            "d-ecp-object": ("gyra_ext.vis.common.tags.gyra_ecp_object", "GyraEcpObject"),
        }

        if vis_type in vis_map:
            try:
                module_path, class_name = vis_map[vis_type]
                module = __import__(module_path, fromlist=[class_name])
                vis_class = getattr(module, class_name)
                instance = vis_class()
                cls._registry[vis_type] = instance
                return instance
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to load vis component '{vis_type}': {e}")

        return None

    @classmethod
    def register(cls, vis_type: str, instance: "Vis") -> None:
        """
        Register a vis component.

        Args:
            vis_type: The type identifier
            instance: The Vis instance
        """
        cls._registry[vis_type] = instance
