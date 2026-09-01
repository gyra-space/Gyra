"""测试媒体生成输入能力适配层：不同 provider / 模型对「首帧 / 尾帧 / 参考图」
支持字段名的差异，以及 executor 在提交前对不支持输入的统一拦截。

覆盖：
- 种子视频(Seedance)：支持 image_url / image_url_last，fast 变体无 image_url_last；
  reference_images 被显式拒绝
- HappyHorse：按模型后缀(-t2v/-i2v/-r2v)分别支持无图/首帧/参考图；不支持尾帧
- 通义万相图像(qwen-image)：支持 image_url / reference_images；不支持尾帧
- 合并协议(volcengine_multimedia / dashscope_multimedia / openai_multimedia /
  google_multimedia)：按 kind 委托内层 provider
- executor._validate_input_capabilities：返回明确的失败原因(而非静默丢弃)
"""

from gyra.agent.multimedia import (
    KIND_IMAGE,
    KIND_VIDEO,
    MultimediaAgentConfig,
    MultimediaExecutor,
    MultimediaRequest,
)
from gyra.agent.tools.result import ResultStatus
from gyra.agent.util.media_gen.base import MediaGenProvider
from gyra.agent.util.media_gen.happyhorse_video_provider import HappyHorseVideoProvider
from gyra.agent.util.media_gen.seedance_video_provider import SeedanceVideoProvider
from gyra.agent.util.media_gen.wanxiang_image_provider import WanxiangImageProvider


class _CapsProvider(MediaGenProvider):
    """按构造参数返回支持集的测试 provider。"""

    def __init__(self, caps):
        super().__init__(api_key="k")
        self._caps = caps

    def supported_image_models(self):
        return []

    def supported_video_models(self):
        return []

    def supported_inputs(self, model, kind=""):
        return set(self._caps)


def _executor():
    return MultimediaExecutor(MultimediaAgentConfig(name="m"))


# ---------------------------------------------------------------------------
# 各 provider 的 supported_inputs
# ---------------------------------------------------------------------------


def test_seedance_supported_inputs():
    p = SeedanceVideoProvider(api_key="k")
    assert p.supported_inputs("doubao-seedance-2-0-250428", KIND_VIDEO) == {
        "image_url",
        "image_url_last",
    }
    # fast 变体不支持首尾帧
    assert p.supported_inputs("doubao-seedance-1-0-pro-fast-250428") == {
        "image_url",
    }


def test_happyhorse_supported_inputs_by_scenario():
    p = HappyHorseVideoProvider(api_key="k")
    assert p.supported_inputs("happyhorse-1.1-t2v") == set()
    assert p.supported_inputs("happyhorse-1.1-i2v") == {"image_url"}
    assert p.supported_inputs("happyhorse-1.1-r2v") == {"reference_images"}
    # 无后缀：按输入推断，两种都允许
    assert p.supported_inputs("happyhorse-1.1") == {
        "image_url",
        "reference_images",
    }


def test_wanxiang_supported_inputs():
    p = WanxiangImageProvider(api_key="k")
    assert p.supported_inputs("qwen-image-3.0-pro", KIND_IMAGE) == {
        "image_url",
        "reference_images",
    }
    assert p.supported_inputs("wan2.6-t2i", KIND_IMAGE) == {"image_url"}


def test_merged_provider_delegates_by_kind():
    from gyra.agent.util.media_gen.dashscope_multimedia_provider import (
        DashScopeMultimediaProvider,
    )
    from gyra.agent.util.media_gen.volcengine_multimedia_provider import (
        VolcengineMultimediaProvider,
    )

    vv = VolcengineMultimediaProvider(api_key="k")
    # kind=video → 内部 Seedance(收窄)；kind=image → 内部 VolcengineImage(未声明→透传)
    assert vv.supported_inputs("doubao-seedance-2-0-250428", KIND_VIDEO) == {
        "image_url",
        "image_url_last",
    }
    assert {"image_url"} <= vv.supported_inputs("some-image-model", KIND_IMAGE)

    dd = DashScopeMultimediaProvider(api_key="k")
    assert dd.supported_inputs("happyhorse-1.1-r2v", KIND_VIDEO) == {
        "reference_images",
    }
    assert dd.supported_inputs("qwen-image-3.0-pro", KIND_IMAGE) == {
        "image_url",
        "reference_images",
    }


# ---------------------------------------------------------------------------
# executor 校验
# ---------------------------------------------------------------------------


def test_validate_unsupported_reference_on_seedance_fails():
    ex = _executor()
    provider = _CapsProvider({"image_url", "image_url_last"})
    req = MultimediaRequest(
        prompt="参考图生视频", kind=KIND_VIDEO, reference_images=["https://a/r.png"]
    )
    err = ex._validate_input_capabilities(KIND_VIDEO, "seedance", provider, req)
    assert err is not None
    assert "reference_images" in err
    assert "seedance" in err


def test_validate_last_frame_without_first_frame_fails():
    ex = _executor()
    provider = _CapsProvider({"image_url", "image_url_last"})
    req = MultimediaRequest(prompt="首尾帧", kind=KIND_VIDEO, image_url_last="https://a/l.png")
    err = ex._validate_input_capabilities(KIND_VIDEO, "seedance", provider, req)
    assert err is not None
    assert "必须与首帧" in err


def test_validate_last_frame_unsupported_model_fails():
    ex = _executor()
    provider = _CapsProvider({"image_url"})  # 无 last_frame
    req = MultimediaRequest(
        prompt="首尾帧", kind=KIND_VIDEO,
        image_url="https://a/f.png", image_url_last="https://a/l.png",
    )
    err = ex._validate_input_capabilities(KIND_VIDEO, "happyhorse-i2v", provider, req)
    assert err is not None
    assert "尾帧" in err


def test_validate_supported_inputs_passes():
    ex = _executor()
    provider = _CapsProvider({"image_url", "image_url_last"})
    req = MultimediaRequest(
        prompt="首尾帧", kind=KIND_VIDEO,
        image_url="https://a/f.png", image_url_last="https://a/l.png",
    )
    assert ex._validate_input_capabilities(KIND_VIDEO, "seedance", provider, req) is None


def test_validate_no_image_input_passes():
    ex = _executor()
    provider = _CapsProvider(set())
    req = MultimediaRequest(prompt="文生视频", kind=KIND_VIDEO)
    assert ex._validate_input_capabilities(KIND_VIDEO, "t2v", provider, req) is None


def test_validate_image_input_on_t2v_model_fails():
    ex = _executor()
    provider = _CapsProvider(set())  # 模型无任何图片输入能力
    req = MultimediaRequest(
        prompt="图生视频", kind=KIND_VIDEO, image_url="https://a/f.png"
    )
    err = ex._validate_input_capabilities(KIND_VIDEO, "happyhorse-t2v", provider, req)
    assert err is not None
    assert "图片输入" in err


# ---------------------------------------------------------------------------
# provider 内部自检 validate_inputs（覆盖工具直调路径）
# ---------------------------------------------------------------------------


def test_seedance_validate_inputs_rejects_reference_images():
    p = SeedanceVideoProvider(api_key="k")
    import pytest

    with pytest.raises(ValueError) as ei:
        p.validate_inputs(
            "doubao-seedance-2-0-250428", KIND_VIDEO, {"reference_images": ["https://a/r.png"]}
        )
    assert "reference_images" in str(ei.value)


def test_seedance_validate_inputs_ok():
    p = SeedanceVideoProvider(api_key="k")
    # 无任何输入 → 不抛
    p.validate_inputs("doubao-seedance-2-0-250428", KIND_VIDEO, {})
    # 首帧 + 尾帧 → 支持
    p.validate_inputs(
        "doubao-seedance-1-5-pro-251215",
        KIND_VIDEO,
        {"image_url": "https://a/f.png", "image_url_last": "https://a/l.png"},
    )


def test_happyhorse_validate_inputs_rejects_last_frame():
    p = HappyHorseVideoProvider(api_key="k")
    import pytest

    with pytest.raises(ValueError):
        p.validate_inputs(
            "happyhorse-1.1-i2v",
            KIND_VIDEO,
            {"image_url": "https://a/f.png", "image_url_last": "https://a/l.png"},
        )


def test_happyhorse_validate_inputs_rejects_reference_on_i2v():
    p = HappyHorseVideoProvider(api_key="k")
    import pytest

    with pytest.raises(ValueError):
        p.validate_inputs(
            "happyhorse-1.1-i2v", KIND_VIDEO, {"reference_images": ["https://a/r.png"]}
        )


def test_wanxiang_validate_inputs_ok_and_rejects_last():
    p = WanxiangImageProvider(api_key="k")
    import pytest

    p.validate_inputs(
        "qwen-image-3.0-pro",
        KIND_IMAGE,
        {"reference_images": ["https://a/a.png", "https://a/b.png"]},
    )
    with pytest.raises(ValueError):
        p.validate_inputs(
            "qwen-image-3.0-pro", KIND_IMAGE, {"image_url_last": "https://a/l.png"}
        )
