"""Vis Plugin."""

import json

from gyra.agent.core.schema import Status
from gyra.util.json_utils import serialize
from gyra.vis.base import Vis


class VisPlugin(Vis):
    """Vis Plugin."""

    @classmethod
    def vis_tag(cls):
        """Vis Plugin."""
        return "vis-plugin"

    def sync_display(self, **kwargs) -> str:
        """Display the content using the vis protocol."""
        content = kwargs.get("content")

        try:
            new_content = {
                "name": content.get("tool_name", ""),
                "args": content.get("tool_args", ""),
                "status": content.get("status", Status.RUNNING.value),
                "logo": content.get("avatar", ""),
                "result": content.get("tool_result", ""),
                "err_msg": content.get("err_msg", ""),
            }
            return f"```{self.vis_tag()}\n{json.dumps(new_content, default=serialize, ensure_ascii=False)}\n```"
        except Exception as e:
            return str(content)
