"""AppCard serve config."""
from dataclasses import dataclass, field
from typing import Optional

from gyra.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from gyra.util.i18n_utils import _
from gyra_serve.core import BaseServeConfig

APP_NAME = "app_card"
SERVE_APP_NAME = "gyra_serve_app_card"
SERVE_APP_NAME_HUMP = "gyra_serve_app_card"
SERVE_CONFIG_KEY_PREFIX = "gyra.serve.app_card."
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"
SERVER_APP_TABLE_NAME = "server_app_app_card"


@auto_register_resource(
    label=_("AppCard Serve Configurations"),
    category=ResourceCategory.COMMON,
    tags={"order": TAGS_ORDER_HIGH},
    description=_("Configuration for the app_card serve module."),
    show_in_ui=False,
)
@dataclass
class ServeConfig(BaseServeConfig):
    __type__ = APP_NAME

    api_keys: Optional[str] = field(
        default=None,
        metadata={"help": _("API keys for app_card serve, comma-separated")},
    )

    def get_type_value(self) -> str:
        return self.__type__
