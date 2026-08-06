"""File Type Configuration for Gyra

Supports dynamic configuration of file processing modes:
- MODEL_DIRECT: Direct model consumption (multimodal messages)
- SANDBOX_TOOL: Sandbox tool consumption

Configuration priority:
1. Environment variable FILE_TYPE_CONFIG (JSON format)
2. Configuration file file_type_config.yaml
3. Default configuration
"""

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)

# Archive/Compressed file extensions (includes composite extensions like .tar.gz)
ARCHIVE_EXTENSIONS = {
    # Single extensions
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    # Composite extensions
    ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz",
    # Other compressed formats
    ".zst", ".lz4", ".lz", ".lzo", ".sz", ".rz", ".jar", ".war", ".ear",
    # Skill package (directory archive)
    ".skill",
}

# Archive/Compressed file MIME types
ARCHIVE_MIME_TYPES = {
    "application/zip",
    "application/x-rar-compressed",
    "application/x-7z-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
    "application/x-bzip2",
    "application/x-xz",
    "application/x-compressed-tar",
    "application/zstd",
    "application/x-lz4",
    "application/java-archive",
    "application/x-java-archive",
}


class FileProcessMode(Enum):
    """File processing mode"""

    MODEL_DIRECT = "model_direct"  # Direct model consumption (multimodal messages)
    SANDBOX_TOOL = "sandbox_tool"  # Sandbox tool consumption


@dataclass
class FileTypeRule:
    """File type rule"""

    extensions: Set[str]  # File extension set, e.g. {".jpg", ".png"}
    mime_types: Set[str]  # MIME type set, e.g. {"image/jpeg", "image/png"}
    mode: FileProcessMode  # Processing mode
    description: str = ""  # Rule description


@dataclass
class FileTypeConfig:
    """File type configuration"""

    # Model direct consumption file types (multimodal)
    model_direct_rules: List[FileTypeRule] = field(default_factory=list)
    # Sandbox tool consumption file types
    sandbox_tool_rules: List[FileTypeRule] = field(default_factory=list)
    # Default processing mode
    default_mode: FileProcessMode = FileProcessMode.SANDBOX_TOOL
    # Enable configuration hot reload
    enable_hot_reload: bool = False

    def get_process_mode(
        self, file_name: str, mime_type: Optional[str] = None
    ) -> FileProcessMode:
        """Get processing mode based on file name and MIME type

        Args:
            file_name: File name
            mime_type: MIME type (optional)

        Returns:
            File processing mode
        """
        # Get file extension
        ext = self._get_extension(file_name)

        # Check model direct rules first (higher priority)
        for rule in self.model_direct_rules:
            if ext in rule.extensions:
                return FileProcessMode.MODEL_DIRECT
            if mime_type and mime_type in rule.mime_types:
                return FileProcessMode.MODEL_DIRECT

        # Check sandbox tool rules
        for rule in self.sandbox_tool_rules:
            if ext in rule.extensions:
                return FileProcessMode.SANDBOX_TOOL
            if mime_type and mime_type in rule.mime_types:
                return FileProcessMode.SANDBOX_TOOL

        # Return default mode
        return self.default_mode

    def _get_extension(self, file_name: str) -> str:
        """Get file extension (lowercase), supports composite extensions like .tar.gz"""
        if not file_name:
            return ""
        name_lower = file_name.lower()
        # Check composite extensions first (longest match)
        for ext in sorted(ARCHIVE_EXTENSIONS, key=len, reverse=True):
            if name_lower.endswith(ext):
                return ext
        # Fallback to single extension
        parts = file_name.rsplit(".", 1)
        if len(parts) == 2:
            return f".{parts[1].lower()}"
        return ""

    def is_model_direct(self, file_name: str, mime_type: Optional[str] = None) -> bool:
        """Check if file should be processed by model directly"""
        return (
            self.get_process_mode(file_name, mime_type) == FileProcessMode.MODEL_DIRECT
        )

    def is_sandbox_tool(self, file_name: str, mime_type: Optional[str] = None) -> bool:
        """Check if file should be processed by sandbox tool"""
        return (
            self.get_process_mode(file_name, mime_type) == FileProcessMode.SANDBOX_TOOL
        )


# Default configuration
DEFAULT_CONFIG = FileTypeConfig(
    model_direct_rules=[
        # Image types - Model direct consumption
        FileTypeRule(
            extensions={".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"},
            mime_types={
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp",
                "image/bmp",
                "image/svg+xml",
            },
            mode=FileProcessMode.MODEL_DIRECT,
            description="Image files (model direct consumption)",
        ),
    ],
    sandbox_tool_rules=[
        # Document types - Sandbox tool consumption
        FileTypeRule(
            extensions={".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
            mime_types={
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
            mode=FileProcessMode.SANDBOX_TOOL,
            description="Document files (sandbox tool consumption)",
        ),
        # Code files - Sandbox tool consumption
        FileTypeRule(
            extensions={
                ".py",
                ".js",
                ".ts",
                ".java",
                ".go",
                ".rs",
                ".cpp",
                ".c",
                ".h",
                ".json",
                ".yaml",
                ".yml",
                ".xml",
                ".sql",
            },
            mime_types={"text/x-python", "application/javascript", "text/javascript"},
            mode=FileProcessMode.SANDBOX_TOOL,
            description="Code files (sandbox tool consumption)",
        ),
        # Data files - Sandbox tool consumption
        FileTypeRule(
            extensions={".csv", ".txt", ".log", ".md", ".json", ".parquet"},
            mime_types={"text/csv", "text/plain", "text/markdown"},
            mode=FileProcessMode.SANDBOX_TOOL,
            description="Data files (sandbox tool consumption)",
        ),
        # Archive files - Sandbox tool consumption
        FileTypeRule(
            extensions=ARCHIVE_EXTENSIONS,
            mime_types=ARCHIVE_MIME_TYPES,
            mode=FileProcessMode.SANDBOX_TOOL,
            description="Archive/compressed files (sandbox tool consumption)",
        ),
    ],
    default_mode=FileProcessMode.SANDBOX_TOOL,
)


class FileTypeConfigManager:
    """File type configuration manager"""

    _instance: Optional["FileTypeConfigManager"] = None
    _config: Optional[FileTypeConfig] = None
    _config_path: Optional[Path] = None
    _last_modified: float = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "FileTypeConfigManager":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_config(self) -> FileTypeConfig:
        """Get current configuration (supports hot reload)"""
        if self._config is None:
            self._load_config()
        elif self._config.enable_hot_reload and self._config_path:
            # Check if configuration file has been updated
            if self._config_path.exists():
                current_modified = self._config_path.stat().st_mtime
                if current_modified > self._last_modified:
                    logger.info("[FileTypeConfig] Config file changed, reloading...")
                    self._load_config()
        return self._config

    def _load_config(self) -> None:
        """Load configuration"""
        # Priority 1: Environment variable
        env_config = os.getenv("FILE_TYPE_CONFIG")
        if env_config:
            try:
                config_dict = json.loads(env_config)
                self._config = self._parse_config_dict(config_dict)
                logger.info("[FileTypeConfig] Loaded config from environment variable")
                return
            except Exception as e:
                logger.warning(f"[FileTypeConfig] Failed to parse env config: {e}")

        # Priority 2: Configuration file
        config_paths = [
            Path("config/file_type_config.yaml"),
            Path("file_type_config.yaml"),
            Path(__file__).parent / "file_type_config.yaml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    self._config = self._load_yaml_config(config_path)
                    self._config_path = config_path
                    self._last_modified = config_path.stat().st_mtime
                    logger.info(f"[FileTypeConfig] Loaded config from {config_path}")
                    return
                except Exception as e:
                    logger.warning(
                        f"[FileTypeConfig] Failed to load {config_path}: {e}"
                    )

        # Priority 3: Default configuration
        self._config = DEFAULT_CONFIG
        logger.info("[FileTypeConfig] Using default config")

    def _load_yaml_config(self, config_path: Path) -> FileTypeConfig:
        """Load YAML configuration file"""
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)
        return self._parse_config_dict(config_dict)

    def _parse_config_dict(self, config_dict: dict) -> FileTypeConfig:
        """Parse configuration dictionary"""
        model_direct_rules = []
        for rule_dict in config_dict.get("model_direct_rules", []):
            model_direct_rules.append(
                FileTypeRule(
                    extensions=set(rule_dict.get("extensions", [])),
                    mime_types=set(rule_dict.get("mime_types", [])),
                    mode=FileProcessMode.MODEL_DIRECT,
                    description=rule_dict.get("description", ""),
                )
            )

        sandbox_tool_rules = []
        for rule_dict in config_dict.get("sandbox_tool_rules", []):
            sandbox_tool_rules.append(
                FileTypeRule(
                    extensions=set(rule_dict.get("extensions", [])),
                    mime_types=set(rule_dict.get("mime_types", [])),
                    mode=FileProcessMode.SANDBOX_TOOL,
                    description=rule_dict.get("description", ""),
                )
            )

        default_mode_str = config_dict.get("default_mode", "sandbox_tool")
        default_mode = FileProcessMode.SANDBOX_TOOL
        if default_mode_str == "model_direct":
            default_mode = FileProcessMode.MODEL_DIRECT

        return FileTypeConfig(
            model_direct_rules=model_direct_rules,
            sandbox_tool_rules=sandbox_tool_rules,
            default_mode=default_mode,
            enable_hot_reload=config_dict.get("enable_hot_reload", False),
        )

    def reload_config(self) -> None:
        """Force reload configuration"""
        self._config = None
        self._load_config()

    def add_model_direct_type(
        self, extension: str, mime_type: Optional[str] = None
    ) -> None:
        """Dynamically add model direct consumption type"""
        config = self.get_config()
        ext = extension if extension.startswith(".") else f".{extension}"

        # Find or create rule
        for rule in config.model_direct_rules:
            if ext not in rule.extensions:
                rule.extensions.add(ext)
                logger.info(
                    f"[FileTypeConfig] Added extension {ext} to model_direct rules"
                )
                return

        # Create new rule
        new_rule = FileTypeRule(
            extensions={ext},
            mime_types={mime_type} if mime_type else set(),
            mode=FileProcessMode.MODEL_DIRECT,
            description=f"Dynamically added: {ext}",
        )
        config.model_direct_rules.append(new_rule)
        logger.info(f"[FileTypeConfig] Created new rule for {ext}")

    def add_sandbox_tool_type(
        self, extension: str, mime_type: Optional[str] = None
    ) -> None:
        """Dynamically add sandbox tool consumption type"""
        config = self.get_config()
        ext = extension if extension.startswith(".") else f".{extension}"

        for rule in config.sandbox_tool_rules:
            if ext not in rule.extensions:
                rule.extensions.add(ext)
                logger.info(
                    f"[FileTypeConfig] Added extension {ext} to sandbox_tool rules"
                )
                return

        new_rule = FileTypeRule(
            extensions={ext},
            mime_types={mime_type} if mime_type else set(),
            mode=FileProcessMode.SANDBOX_TOOL,
            description=f"Dynamically added: {ext}",
        )
        config.sandbox_tool_rules.append(new_rule)
        logger.info(f"[FileTypeConfig] Created new rule for {ext}")


def get_file_process_mode(
    file_name: str, mime_type: Optional[str] = None
) -> FileProcessMode:
    """Convenience function: get file processing mode"""
    manager = FileTypeConfigManager.get_instance()
    config = manager.get_config()
    return config.get_process_mode(file_name, mime_type)


def is_model_direct_file(file_name: str, mime_type: Optional[str] = None) -> bool:
    """Convenience function: check if file should be processed by model directly"""
    return get_file_process_mode(file_name, mime_type) == FileProcessMode.MODEL_DIRECT


def is_sandbox_tool_file(file_name: str, mime_type: Optional[str] = None) -> bool:
    """Convenience function: check if file should be processed by sandbox tool"""
    return get_file_process_mode(file_name, mime_type) == FileProcessMode.SANDBOX_TOOL


# ---------------------------------------------------------------------------
# 统一分流决策（capability-aware）
# ---------------------------------------------------------------------------
# 两条分流路径（file_dispatch.detect_dispatch_type、sandbox_file_ref.process_user_input_file）
# 都汇入这里的 decide_process_mode，消除规则不一致。判定依据：
#   1. 非多媒体文件（文档/代码/压缩/数据/未知）→ 永远 SANDBOX_TOOL（工具消费）
#   2. 多媒体文件 + 多媒体 agent（prefer_direct_media）→ MODEL_DIRECT
#   3. 多媒体文件 + 模型能力标签包含所需模态 → MODEL_DIRECT（直接模型消费）
#   4. 否则（模型不支持该模态）→ SANDBOX_TOOL（先入沙箱，由 agent 经工具/子 agent 委派）
# ---------------------------------------------------------------------------

# 文件模态 → 模型所需能力标签
MODALITY_CAPABILITY = {
    "image": "vision",
    "audio": "audio",
    "video": "video",
}

# 各模态的扩展名集合
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff",
}
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma", ".opus",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm", ".m4v",
}

MODALITY_EXTENSIONS = {
    "image": IMAGE_EXTENSIONS,
    "audio": AUDIO_EXTENSIONS,
    "video": VIDEO_EXTENSIONS,
}


def detect_file_modality(
    file_name: str, mime_type: Optional[str] = None
) -> Optional[str]:
    """检测文件模态：返回 "image" / "audio" / "video"；非多媒体返回 None。"""
    if not file_name and not mime_type:
        return None

    if file_name:
        ext = file_name.lower()
        if "." in ext:
            base, _, suffix = ext.rpartition(".")
            ext = "." + suffix
        for modality, extensions in MODALITY_EXTENSIONS.items():
            if ext in extensions:
                return modality

    if mime_type:
        prefix = (mime_type or "").split("/")[0].lower()
        if prefix in ("image", "audio", "video"):
            return prefix

    return None


def decide_process_mode(
    file_name: str,
    mime_type: Optional[str] = None,
    capabilities: Optional[List[str]] = None,
    prefer_direct_media: bool = False,
) -> FileProcessMode:
    """统一分流决策：结合文件类型 + 当前 agent 模型能力。

    Args:
        file_name: 文件名。
        mime_type: MIME 类型（可选）。
        capabilities: 当前 agent 所用模型的能力标签列表，如 ["text", "vision"]。
        prefer_direct_media: 是否为多媒体 agent（图片/视频直接消费）。

    Returns:
        FileProcessMode.MODEL_DIRECT 或 FileProcessMode.SANDBOX_TOOL。
    """
    modality = detect_file_modality(file_name, mime_type)
    if modality is None:
        return FileProcessMode.SANDBOX_TOOL

    if prefer_direct_media:
        return FileProcessMode.MODEL_DIRECT

    need = MODALITY_CAPABILITY.get(modality)
    caps = capabilities or []
    if need and need in caps:
        return FileProcessMode.MODEL_DIRECT

    return FileProcessMode.SANDBOX_TOOL


def resolve_model_capabilities(model_name: Optional[str]) -> List[str]:
    """解析模型的多模态能力标签列表（供分流决策使用）。

    复用全局/空间级 ModelConfigCache，空间绑定模型时自动生效。
    """
    if not model_name:
        return []
    try:
        from gyra.agent.util.llm.model_config_cache import ModelConfigCache

        return list(ModelConfigCache.get_capabilities(model_name))
    except Exception:  # noqa: BLE001 - 解析失败按无能力处理
        return []


def is_multimedia_agent(
    gpt_app: Any = None,
    app_ext_config: Optional[Dict[str, Any]] = None,
    app_code: Optional[str] = None,
) -> bool:
    """判断某 agent/app 是否为多媒体 agent（ext_config.multimedia_agent.enabled）。

    Args:
        gpt_app: 已加载的 GptsApp 实例（agent_chat 内可用）。
        app_ext_config: 已解析的 ext_config dict（可选）。
        app_code: app 编码（可选，未给实例/配置时按编码查库兜底）。
    """
    cfg = app_ext_config
    if not cfg and gpt_app is not None:
        cfg = getattr(gpt_app, "ext_config", None)
    gold = cfg

    def _from_cfg(c):
        if isinstance(c, str):
            try:
                import json as _json
                c = _json.loads(c)
            except Exception:  # noqa: BLE001
                return False
        if isinstance(c, dict):
            raw = c.get("multimedia_agent")
            return bool(raw and raw.get("enabled", True))
        return False

    if gold is not None:
        return _from_cfg(gold)

    if app_code:
        try:
            from gyra_serve.agent.db.gpts_app import GptsAppDao

            app = GptsAppDao().app_detail(app_code)
            if app is not None:
                return _from_cfg(getattr(app, "ext_config", None))
        except Exception:  # noqa: BLE001 - 查库失败按非多媒体处理
            pass

    return False
