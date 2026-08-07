"""Secrets（加密密钥）的数据库持久化。

密钥值始终以 **加密密文** 形式存储（Fernet/AES，见
``gyra_core.config.encryption.SecretsEncryption``），数据库只保存加密后的密文，
不落任何明文。数据库为准（分布式多节点共享同一份密钥），同时保留本地
``~/.gyra/secrets.enc`` 作为备份。

存储格式：``system_config`` 表中以 ``config_key="secrets"``、``config_type="secret"``
单行保存整个 ``{name: encrypted_value}`` 字典。
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_SECRETS_CONFIG_KEY = "secrets"
_SECRETS_CONFIG_TYPE = "secret"


def _dao():
    from gyra_app.feature_plugins.system_config_dao import SystemConfigDao

    return SystemConfigDao()


def load_encrypted_secrets() -> Optional[Dict[str, Any]]:
    """从数据库读取加密密钥字典 {name: encrypted_value}，无记录返回 None。"""
    try:
        data = _dao().get_config(_SECRETS_CONFIG_KEY, _SECRETS_CONFIG_TYPE)
        if data and isinstance(data, dict):
            # 兼容历史可能存在的 {"secrets": {...}} 包装
            if "secrets" in data and isinstance(data["secrets"], dict):
                return data["secrets"]
            return data
    except Exception as e:  # pragma: no cover - best-effort DB read
        logger.warning(f"Failed to load secrets from database: {e}")
    return None


def save_encrypted_secrets(encrypted_secrets: Dict[str, Any]) -> bool:
    """将加密密钥字典写入数据库（upsert，数据库为准）。"""
    try:
        _dao().set_config(
            _SECRETS_CONFIG_KEY,
            encrypted_secrets,
            _SECRETS_CONFIG_TYPE,
            description="加密密钥（Secret，数据库为准，分布式共享）",
        )
        return True
    except Exception as e:
        logger.exception(f"Failed to save secrets to database: {e}")
        return False


def delete_encrypted_secrets() -> bool:
    """删除数据库中的密钥记录。"""
    try:
        return _dao().delete_config(_SECRETS_CONFIG_KEY, _SECRETS_CONFIG_TYPE)
    except Exception as e:  # pragma: no cover - best-effort delete
        logger.warning(f"Failed to delete secrets from database: {e}")
        return False