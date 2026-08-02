from gyra import BaseComponent, SystemApp
from gyra.agent.core.reasoning.reasoning_engine import ReasoningEngine
from gyra.component import ComponentType
from gyra.core.awel import BaseOperator

_HAS_SCAN = False


class ReasoningManage(BaseComponent):
    name = ComponentType.REASONING_MANAGER

    def init_app(self, system_app: SystemApp):
        pass

    def after_start(self):
        global _HAS_SCAN

        if _HAS_SCAN:
            return

        _register()

        _HAS_SCAN = True


def _register():
    from gyra.util.module_utils import ModelScanner, ScannerConfig

    # from gyra_ext.reasoning_engine.default_reasoning_engine import DefaultReasoningEngine
    # ReasoningEngine.register(DefaultReasoningEngine)

    for baseclass, path in [
        (ReasoningEngine, "gyra_ext.reasoning_engine"),
        (BaseOperator, "gyra_ext.agent.agents.awel"),
    ]:
        scanner = ModelScanner[baseclass]()
        config = ScannerConfig(
            module_path=path,
            base_class=baseclass,
            recursive=True,
        )
        scanner.scan_and_register(config)
        if hasattr(baseclass, "register"):
            for _, subclass in scanner.get_registered_items().items():
                baseclass.register(subclass=subclass)
