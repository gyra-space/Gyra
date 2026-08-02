import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic_core._pydantic_core import ValidationError

from gyra._private.pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_to_json,
    model_validator,
    model_to_dict,
)
from gyra.agent.core.action.base import OutputType
from gyra.vis import Vis
from gyra.vis.schema import VisStepContent, VisBase

logger = logging.getLogger(__name__)

class ToolSpace(Vis):
    """Monitor Space."""

    def __init__(self, **kwargs):
        self._gyra_web_url = kwargs.get("gyra_web_url", "")
        super().__init__(**kwargs)

    def sync_generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
        content = kwargs["content"]
        try:
            VisStepContent.model_validate(content)
            return content
        except ValidationError as e:
            logger.warning(
                f"ToolSpace可视化组件收到了非法的数据内容，可能导致显示失败！{content}"
            )
            return content

    @classmethod
    def vis_tag(cls):
        """Vis tag name.

        Returns:
            str: The tag name associated with the visualization.
        """
        return "d-tool"
