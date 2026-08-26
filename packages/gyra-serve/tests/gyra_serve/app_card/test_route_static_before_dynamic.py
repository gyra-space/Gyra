"""路由注册顺序的回归测试: 动态路径 `/app_cards/{card_id}/invoke` 必须注册在所有静态路径之后。

FastAPI 按注册顺序匹配, 若动态路由先注册, `POST /app_cards/preview/invoke` 会把 "preview"
当作 card_id 解析(报 `path.card_id: Input should be a valid integer`)且因该路由要求
`workspace_id` query 而报 `query.workspace_id: Field required`, 静态路由被永久遮蔽。
`/app_cards/share/invoke` 同理(把 "share" 当 card_id)。

这里直接用 Starlette 的路由匹配语义验证: 每个请求路径应命中的第一个 FULL match 是静态路由,
而非被 `{card_id}` 动态路由抢先。
"""
from starlette.routing import Match

from gyra_serve.app_card.api import endpoints as ep


def _first_full_route(method: str, path: str):
    scope = {"type": "http", "method": method, "path": path}
    for route in ep.router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route
    return None


def test_preview_invoke_hits_static_route():
    route = _first_full_route("POST", "/app_cards/preview/invoke")
    assert route is not None
    assert route.path == "/app_cards/preview/invoke", (
        f"preview/invoke 被动态路由抢先命中: {route.path}"
    )


def test_share_invoke_hits_static_route():
    route = _first_full_route("POST", "/app_cards/share/invoke")
    assert route is not None
    assert route.path == "/app_cards/share/invoke", (
        f"share/invoke 被动态路由抢先命中: {route.path}"
    )


def test_real_card_id_invoke_hits_dynamic_route():
    route = _first_full_route("POST", "/app_cards/123/invoke")
    assert route is not None
    assert route.path == "/app_cards/{card_id}/invoke"
