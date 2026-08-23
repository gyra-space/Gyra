"""Gyra 版本号 — 唯一权威源。

版本号统一维护在项目根目录 ``packages/__init__.py`` 的 ``__version__``，
本模块只是它的转发层，避免 gyra 库内部出现第二套版本号（历史原因曾有 0.7.0 漂移）。

升级版本请修改：packages/__init__.py
"""

try:
    # 优先引用唯一权威源（项目根目录 packages/__init__.py）
    from packages import __version__ as _packages_version
except Exception:  # pragma: no cover - 安装场景兜底
    _packages_version = "0.0.0"

version = _packages_version
