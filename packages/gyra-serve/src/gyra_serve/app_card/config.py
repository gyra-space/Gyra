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
    query_timeout_seconds: int = field(
        default=60,
        metadata={"help": _("单条 SQL 执行超时(秒), 由数据库强制生效, 0 不限时")},
    )
    query_max_workers: int = field(
        default=8,
        metadata={"help": _("应用卡片 SQL 专用线程池的并发工作线程数")},
    )
    query_max_queue: int = field(
        default=8,
        metadata={"help": _("超过并发后在队列中等待的最大任务数, 超出即快速失败")},
    )
    query_queue_wait_seconds: float = field(
        default=5.0,
        metadata={"help": _("任务在队列中等待槽位的最长时间(秒), 超时快速失败")},
    )
    max_result_rows: int = field(
        default=100000,
        metadata={"help": _("单次最大返回行数(熔断上限), 超出则截断标记 truncated")},
    )
    result_cache_ttl_seconds: float = field(
        default=30.0,
        metadata={"help": _("查询结果缓存的存活时间(秒), 0 表示关闭缓存")},
    )
    result_cache_max_entries: int = field(
        default=256,
        metadata={"help": _("查询结果缓存的最大条目数(LRU 淘汰)")},
    )

    def get_type_value(self) -> str:
        return self.__type__
