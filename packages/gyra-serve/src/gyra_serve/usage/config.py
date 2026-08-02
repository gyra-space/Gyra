"""LLM usage serve configuration."""

from dataclasses import dataclass, field
from typing import Optional

from gyra.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from gyra.util.i18n_utils import _
from gyra_serve.core import BaseServeConfig

APP_NAME = "usage"
SERVE_APP_NAME = "gyra_serve_usage"
SERVE_APP_NAME_HUMP = "gyra_serve_Usage"
SERVE_CONFIG_KEY_PREFIX = "gyra.serve.usage."
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"
# Database table name
SERVER_APP_TABLE_NAME = "gyra_serve_llm_usage"


@auto_register_resource(
    label=_("LLM Usage Serve Configurations"),
    category=ResourceCategory.COMMON,
    tags={"order": TAGS_ORDER_HIGH},
    description=_("Configuration for the LLM usage (token/cost) serve module."),
    show_in_ui=False,
)
@dataclass
class ServeConfig(BaseServeConfig):
    """Configuration for the LLM usage serve module."""

    __type__ = APP_NAME

    enabled: bool = field(
        default=True,
        metadata={"help": _("Enable LLM usage recording")},
    )
    api_keys: Optional[str] = field(
        default=None,
        metadata={"help": _("Comma-separated API keys; empty means no auth")},
    )
