import logging
from typing import List, Dict, Any, Optional, Union

from pydantic_core._pydantic_core import ValidationError

from gyra.vis import Vis
from gyra._private.pydantic import (
    Field,
    model_to_dict,
)
from gyra_ext.vis.common.tags.gyra_work_space import WorkSpaceContent
from gyra_ext.vis.gyra.tags.drsk_base import DrskVisBase
from gyra_ext.vis.gyra.tags.nex_running_window import RunningContent

logger = logging.getLogger(__name__)


class RunningWindowContent(DrskVisBase):
    running_agent: Optional[Union[str, List[str]]] = Field(None, description="agent role")
    items: List[Union[WorkSpaceContent, RunningContent]] = Field(default=[], description="work agent items")

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        tasks_dict = []
        for step in self.items:
            tasks_dict.append(step.to_dict())
        dict_value = model_to_dict(self, exclude={"items"})
        dict_value["items"] = tasks_dict
        return dict_value


class GyraRunningWindow(Vis):
    """GyraRunningWindow."""

    def sync_generate_param(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate the parameters required by the gyra_vis protocol.

        Display corresponding content using gyra_vis protocol

        Args:
            **kwargs:

        Returns:
        gyra_vis protocol text
        """
        content = kwargs["content"]
        try:
            RunningWindowContent.model_validate(content)
            return content
        except ValidationError as e:
            logger.warning(
                f"GyraRunningWindow可视化组件收到了非法的数据内容，可能导致显示失败！{content}"
            )
            return content

    @classmethod
    def vis_tag(cls):
        """Vis tag name.

        Returns:
            str: The tag name associated with the visualization.
        """
        return "gyra-running-window"
