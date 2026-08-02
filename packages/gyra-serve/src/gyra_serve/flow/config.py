from dataclasses import dataclass, field
from typing import Optional

from gyra.core.awel.flow import (
    TAGS_ORDER_HIGH,
    ResourceCategory,
    auto_register_resource,
)
from gyra.util.i18n_utils import _
from gyra_serve.core import BaseServeConfig

APP_NAME = "flow"
SERVE_APP_NAME = "gyra_serve_flow"
SERVE_APP_NAME_HUMP = "gyra_serve_Flow"
SERVE_CONFIG_KEY_PREFIX = "gyra.serve.flow."
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"
SERVE_VARIABLES_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_variables_service"
# Database table name
SERVER_APP_TABLE_NAME = "gyra_serve_flow"
SERVER_APP_VARIABLES_TABLE_NAME = "gyra_serve_variables"


@auto_register_resource(
    label=_("AWEL Flow Serve Configurations"),
    category=ResourceCategory.COMMON,
    tags={"order": TAGS_ORDER_HIGH},
    description=_("This configuration is for the flow serve module."),
    show_in_ui=False,
)
@dataclass
class ServeConfig(BaseServeConfig):
    """Parameters for the serve command"""

    __type__ = APP_NAME

    load_gyras_interval: int = field(
        default=5,
        metadata={"help": _("Interval to load gyras from installed packages")},
    )
    encrypt_key: Optional[str] = field(
        default=None, metadata={"help": _("The key to encrypt the data")}
    )
