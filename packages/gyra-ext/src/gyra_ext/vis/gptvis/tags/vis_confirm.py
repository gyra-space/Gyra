from gyra.vis import Vis, SystemVisTag


class VisConfirm(Vis):
    def vis_tag(cls) -> str:
        return "vis-confirm"
