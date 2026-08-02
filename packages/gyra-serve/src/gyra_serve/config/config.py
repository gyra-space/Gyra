from dataclasses import dataclass, field
from typing import List

from gyra.util.i18n_utils import _
from gyra.util.module_utils import ScannerConfig
from gyra_serve.config.service.base_upload import UpdaterConfig
from gyra_serve.core import BaseServeConfig

APP_NAME = "config"
SERVE_APP_NAME = "gyra_serve_config"
SERVE_APP_NAME_HUMP = "gyra_serve_Config"
SERVE_CONFIG_KEY_PREFIX = "gyra_serve.config."
SERVE_SERVICE_COMPONENT_NAME = f"{SERVE_APP_NAME}_service"
# Database table name
SERVER_APP_TABLE_NAME = "gyra_serve_config"


@dataclass
class ServeConfig(BaseServeConfig):
    """Parameters for the serve command"""

    __type__ = APP_NAME

    __scan_config__ = ScannerConfig(
        module_path="gyra_serve.config.service.ext",
        base_class=UpdaterConfig,
        recursive=True,
        # specific_files=["config"],
    )


    config_update_interval: int = field(
        default=60,
        metadata={"help": _("Interval to update from config updater")},
    )
    updaters: List[UpdaterConfig] = field(
        default_factory=list,
        metadata={"help": _("The updaters configurations")},
    )