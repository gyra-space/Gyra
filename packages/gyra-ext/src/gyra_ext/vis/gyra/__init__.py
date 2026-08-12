import importlib
from typing import Any

__all__ = [
    "GyraIncrVisWindow2Converter",
    "GyraIncrVisWindow3Converter",
    "GyraVisIncrConverter",
    "GyraVisConverter",
]

_LAZY_IMPORTS = {
    "GyraIncrVisWindow2Converter": ".gyra_vis_window2_converter",
    "GyraIncrVisWindow3Converter": ".gyra_vis_window3_converter",
    "GyraVisIncrConverter": ".gyra_vis_incr_converter",
    "GyraVisConverter": ".gyra_vis_converter",
}


def __getattr__(name: str) -> Any:
    """Lazy-load converter classes to break the import cycle.

    Importing ``gyra_ext.vis.gyra.tags.*`` triggers this package's
    ``__init__``; eagerly importing the converters here would in turn import
    ``gyra_ext.vis.common.tags.gyra_thinking`` while it is still partially
    initialized, raising a circular import error.
    """
    if name in _LAZY_IMPORTS:
        module = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")