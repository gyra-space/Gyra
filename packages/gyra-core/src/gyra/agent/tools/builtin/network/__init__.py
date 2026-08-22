"""
网络工具模块 - 已迁移到统一工具框架

提供Agent的网络访问能力：
- WebFetchTool: 获取网页内容
- WebSearchTool: 网络搜索
- APICallTool: API调用
"""

from typing import Any, Dict, List, Optional
import logging
import asyncio
import json
import os
import re
from urllib.parse import urlparse

from ...base import ToolBase, ToolCategory, ToolRiskLevel, ToolSource
from ...metadata import ToolMetadata
from ...result import ToolResult
from ...context import ToolContext

logger = logging.getLogger(__name__)


class WebFetchTool(ToolBase):
    """获取网页内容工具 - 已迁移"""

    def __init__(self, http_client: Optional[Any] = None, timeout: int = 30):
        self._http_client = http_client
        self._timeout = timeout
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="webfetch",
            display_name="Web Fetch",
            description=(
                "Fetch content from a specified URL. "
                "Takes a URL and optional format as input. "
                "Fetches the URL content, converts to requested format (markdown by default). "
                "Returns the content in the specified format. "
                "Use this tool when you need to retrieve and analyze web content."
            ),
            category=ToolCategory.NETWORK,
            risk_level=ToolRiskLevel.MEDIUM,
            source=ToolSource.SYSTEM,
            requires_permission=True,
            tags=["network", "web", "fetch", "http"],
            timeout=30,
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from",
                },
                "format": {
                    "type": "string",
                    "description": "Format to return content in",
                    "enum": ["markdown", "text", "html", "json"],
                    "default": "markdown",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (max 120)",
                    "default": 30,
                    "maximum": 120,
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["url"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        url = args.get("url", "")
        format_type = args.get("format", "markdown")
        timeout = min(args.get("timeout", self._timeout), 120)
        headers = args.get("headers", {})

        if not url:
            return ToolResult(
                success=False, output="", error="URL不能为空", tool_name=self.name
            )

        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
            elif parsed.scheme not in ["http", "https"]:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"不支持的协议: {parsed.scheme}",
                    tool_name=self.name,
                )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"无效的URL: {e}", tool_name=self.name
            )

        try:
            if self._http_client:
                content = await self._fetch_with_client(url, headers, timeout)
            else:
                content = await self._fetch_with_aiohttp(url, headers, timeout)

            output = self._format_content(content, format_type)

            return ToolResult(
                success=True,
                output=output,
                tool_name=self.name,
                metadata={
                    "url": url,
                    "format": format_type,
                    "content_length": len(output),
                },
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"请求超时 ({timeout}秒)",
                tool_name=self.name,
            )
        except Exception as e:
            logger.error(f"[WebFetchTool] 请求失败: {e}")
            return ToolResult(
                success=False, output="", error=str(e), tool_name=self.name
            )

    async def _fetch_with_client(
        self, url: str, headers: Dict[str, str], timeout: int
    ) -> str:
        if hasattr(self._http_client, "get"):
            response = await self._http_client.get(
                url, headers=headers, timeout=timeout
            )
            return await response.text()
        raise ValueError("HTTP client not properly configured")

    async def _fetch_with_aiohttp(
        self, url: str, headers: Dict[str, str], timeout: int
    ) -> str:
        try:
            import aiohttp

            default_headers = {
                "User-Agent": "Mozilla/5.0 (compatible; GyraAgent/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            default_headers.update(headers)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=default_headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status >= 400:
                        raise ValueError(f"HTTP错误: {response.status}")
                    return await response.text()
        except ImportError:
            return await self._fetch_with_httpx(url, headers, timeout)

    async def _fetch_with_httpx(
        self, url: str, headers: Dict[str, str], timeout: int
    ) -> str:
        try:
            import httpx

            default_headers = {
                "User-Agent": "Mozilla/5.0 (compatible; GyraAgent/1.0)",
            }
            default_headers.update(headers)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=default_headers, timeout=timeout
                )
                response.raise_for_status()
                return response.text
        except ImportError:
            raise ImportError(
                "需要安装 aiohttp 或 httpx: pip install aiohttp 或 pip install httpx"
            )

    def _format_content(self, content: str, format_type: str) -> str:
        if format_type == "html":
            return content
        elif format_type == "text":
            return self._html_to_text(content)
        elif format_type == "json":
            return self._extract_json(content)
        else:
            return self._html_to_markdown(content)

    def _html_to_text(self, html: str) -> str:
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(
            r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE
        )
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _html_to_markdown(self, html: str) -> str:
        text = self._html_to_text(html)

        lines = text.split("\n")
        result = []
        for line in lines:
            line = line.strip()
            if line:
                result.append(line)

        return "\n\n".join(result)

    def _extract_json(self, content: str) -> str:
        # 优先直接解析整段响应：多数 JSON API（如 open-meteo）返回裸 JSON，
        # 不包在 <script>/<pre> 标签里，原正则永远匹配不到。
        text = content.strip()
        if text:
            try:
                data = json.loads(text)
                return json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

        # 兜底：从 HTML 里的 <script type="application/json"> / <pre> 提取
        json_pattern = r'<(?:script[^>]*type=["\']application/json["\'][^>]*|pre)[^>]*>(.*?)</(?:script|pre)>'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)

        json_objects = []
        for match in matches:
            try:
                data = json.loads(match.strip())
                json_objects.append(data)
            except json.JSONDecodeError:
                continue

        if json_objects:
            return json.dumps(json_objects, indent=2, ensure_ascii=False)

        return "未找到JSON内容"


class WebSearchTool(ToolBase):
    """网络搜索工具 - 已迁移"""

    def __init__(
        self,
        search_engine: Optional[Any] = None,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ):
        self._search_engine = search_engine
        self._api_key = api_key
        self._search_engine_id = search_engine_id
        super().__init__()

    def _define_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="websearch",
            display_name="Web Search",
            description=(
                "Search the web for information. "
                "Returns search results with titles, URLs, and snippets. "
                "Use this tool when you need to find information on the internet."
            ),
            category=ToolCategory.NETWORK,
            risk_level=ToolRiskLevel.MEDIUM,
            source=ToolSource.SYSTEM,
            requires_permission=True,
            tags=["network", "search", "web", "google"],
            timeout=30,
        )

    def _define_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 10,
                    "maximum": 20,
                },
                "lang": {
                    "type": "string",
                    "description": "Language for search results",
                    "default": "en",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self, args: Dict[str, Any], context: Optional[ToolContext] = None
    ) -> ToolResult:
        query = args.get("query", "")
        num_results = min(args.get("num_results", 10), 20)
        lang = args.get("lang", "en")

        if not query:
            return ToolResult(
                success=False, output="", error="搜索查询不能为空", tool_name=self.name
            )

        try:
            if self._search_engine:
                results = await self._search_with_engine(query, num_results, lang)
            else:
                results = await self._search_with_serp(query, num_results, lang)

            if not results:
                return ToolResult(
                    success=True,
                    output="未找到搜索结果",
                    tool_name=self.name,
                    metadata={"query": query, "count": 0},
                )

            output_lines = [f"搜索: {query}\n"]
            for i, result in enumerate(results, 1):
                output_lines.append(f"\n{i}. {result.get('title', '无标题')}")
                output_lines.append(f"   URL: {result.get('url', 'N/A')}")
                output_lines.append(f"   {result.get('snippet', '无摘要')}")

            return ToolResult(
                success=True,
                output="\n".join(output_lines),
                tool_name=self.name,
                metadata={"query": query, "count": len(results), "results": results},
            )

        except Exception as e:
            logger.error(f"[WebSearchTool] 搜索失败: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"搜索失败: {str(e)}",
                tool_name=self.name,
            )

    async def _search_with_engine(self, query: str, num: int, lang: str) -> List[Dict]:
        """使用配置的搜索引擎"""
        if hasattr(self._search_engine, "search"):
            return await self._search_engine.search(query, num_results=num, lang=lang)
        return []

    async def _search_with_serp(self, query: str, num: int, lang: str) -> List[Dict]:
        """使用 SerpAPI；未配置密钥或调用失败时依次兜底 DuckDuckGo / Bing / 百度"""
        if self._api_key:
            try:
                import aiohttp

                url = "https://serpapi.com/search"
                params = {
                    "q": query,
                    "api_key": self._api_key,
                    "engine": "google",
                    "num": num,
                    "hl": lang,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        data = await response.json()

                        results = []
                        for item in data.get("organic_results", [])[:num]:
                            results.append(
                                {
                                    "title": item.get("title"),
                                    "url": item.get("link"),
                                    "snippet": item.get("snippet", ""),
                                }
                            )
                        if results:
                            return results
            except Exception as e:
                logger.warning(f"SerpAPI搜索调用失败，尝试兜底搜索: {e}")

        # 默认兜底链路（无需任何配置）：DuckDuckGo -> Bing -> 百度，逐一尝试
        return await self._search_with_free_engines(query, num, lang)

    async def _search_with_free_engines(
        self, query: str, num: int, lang: str
    ) -> List[Dict]:
        """依次尝试 DuckDuckGo / Bing / 百度 免费搜索，任一成功即返回"""
        for engine in ("duckduckgo", "bing", "baidu"):
            try:
                results = await self._search_with_engine_html(query, num, engine)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"免费搜索[{engine}]失败: {e}")
        return self._mock_search_results(query, num)

    async def _search_with_engine_html(
        self, query: str, num: int, engine: str
    ) -> List[Dict]:
        """爬取指定免费搜索引擎的 HTML 结果"""
        import aiohttp
        from urllib.parse import quote

        if engine == "duckduckgo":
            url = "https://html.duckduckgo.com/html/?q=" + quote(query)
        elif engine == "bing":
            url = "https://www.bing.com/search?q=" + quote(query)
        elif engine == "baidu":
            url = "https://www.baidu.com/s?wd=" + quote(query)
        else:
            return []

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status >= 400:
                    raise ValueError(f"{engine} HTTP错误: {response.status}")
                html = await response.text()

        if engine == "duckduckgo":
            results = self._parse_duckduckgo_html(html)
        elif engine == "bing":
            results = self._parse_bing_html(html)
        elif engine == "baidu":
            results = self._parse_baidu_html(html)
        else:
            results = []
        return results[:num]

    def _parse_duckduckgo_html(self, html: str) -> List[Dict]:
        """解析 DuckDuckGo HTML 搜索结果"""
        import html as _html

        title_re = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        snippet_re = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        titles = title_re.findall(html)
        snippets = snippet_re.findall(html)

        def _clean(value: str) -> str:
            return _html.unescape(re.sub(r"<[^>]+>", "", value)).strip()

        results = []
        for i, (href, title) in enumerate(titles):
            results.append(
                {
                    "title": _clean(title),
                    "url": self._decode_ddg_url(href),
                    "snippet": _clean(snippets[i]) if i < len(snippets) else "",
                }
            )
        return results

    def _decode_ddg_url(self, href: str) -> str:
        """解码 DuckDuckGo 的重定向链接为真实 URL"""
        from urllib.parse import urlparse, parse_qs

        qs = parse_qs(urlparse(href).query)
        uddg = qs.get("uddg")
        return uddg[0] if uddg else href

    def _parse_bing_html(self, html: str) -> List[Dict]:
        """解析 Bing 搜索结果 HTML"""
        import html as _html

        item_re = re.compile(
            r'<li class="b_algo".*?</li>', re.DOTALL | re.IGNORECASE
        )
        title_re = re.compile(r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
        snippet_re = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)

        def _clean(value: str) -> str:
            return _html.unescape(re.sub(r"<[^>]+>", "", value)).strip()

        results = []
        for item in item_re.findall(html):
            title_m = title_re.search(item)
            if not title_m:
                continue
            href, title = title_m.groups()
            snippet_m = snippet_re.search(item)
            results.append(
                {
                    "title": _clean(title),
                    "url": href,
                    "snippet": _clean(snippet_m.group(1)) if snippet_m else "",
                }
            )
        return results

    def _parse_baidu_html(self, html: str) -> List[Dict]:
        """解析百度搜索结果 HTML"""
        import html as _html

        item_re = re.compile(
            r'<div[^>]*class="[^"]*result[^"]*c-container[^"]*".*?</div>',
            re.DOTALL | re.IGNORECASE,
        )
        title_re = re.compile(r"<h3[^>]*>\s*<a[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
        snippet_re = re.compile(r'<span[^>]*class="[^"]*content-right_[^"]*"[^>]*>(.*?)</span>|<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>', re.DOTALL | re.IGNORECASE)

        def _clean(value: str) -> str:
            return _html.unescape(re.sub(r"<[^>]+>", "", value)).strip()

        results = []
        for item in item_re.findall(html):
            title_m = title_re.search(item)
            if not title_m:
                continue
            href, title = title_m.groups()
            snippet_m = snippet_re.search(item)
            snippet = ""
            if snippet_m:
                snippet = snippet_m.group(1) or snippet_m.group(2) or ""
            results.append(
                {
                    "title": _clean(title),
                    "url": href,
                    "snippet": _clean(snippet),
                }
            )
        return results

    def _mock_search_results(self, query: str, num: int) -> List[Dict]:
        """模拟搜索结果（用于测试）"""
        return [
            {
                "title": f"搜索结果 {i + 1} for: {query}",
                "url": f"https://example.com/result/{i + 1}",
                "snippet": f"这是关于 '{query}' 的模拟搜索结果 {i + 1}。请配置搜索API以获取真实结果。",
            }
            for i in range(min(num, 3))
        ]


def register_network_tools(
    registry: "ToolRegistry", http_client: Optional[Any] = None
) -> None:
    """注册网络工具"""
    from ...registry import ToolRegistry

    registry.register(WebFetchTool(http_client=http_client))

    # 可选配置：设置 SERP_API_KEY 后优先使用 SerpAPI(Google) 搜索；
    # 未配置时 WebSearchTool 默认兜底走 DuckDuckGo 免费搜索，无需任何配置
    api_key = os.getenv("SERP_API_KEY")
    registry.register(WebSearchTool(api_key=api_key or None))
    logger.info("[NetworkTools] 已注册网络工具: webfetch, websearch")
