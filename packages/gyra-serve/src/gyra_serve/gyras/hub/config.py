from dataclasses import dataclass

from gyra.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from gyra.util.i18n_utils import _
from gyra_serve.core import BaseServeConfig

APP_NAME = "gyras_hub"
SERVE_APP_NAME = "gyra_serve_gyras_hub"
SERVE_APP_NAME_HUMP = "gyra_serve_GyrasHub"
SERVE_CONFIG_KEY_PREFIX = "gyra.serve.gyras_hub."
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"
# Database table name
SERVER_APP_TABLE_NAME = SERVE_APP_NAME


@auto_register_resource(
    label=_("Hub gyras Serve Configurations"),
    category=ResourceCategory.COMMON,
    tags={"order": TAGS_ORDER_HIGH},
    description=_("This configuration is for the hub gyras serve module."),
    show_in_ui=False,
)
@dataclass
class ServeConfig(BaseServeConfig):
    """Parameters for the serve command"""

    __type__ = APP_NAME
