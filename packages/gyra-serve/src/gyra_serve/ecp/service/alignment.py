"""LLM-driven semantic alignment between knowledge entities and hard-layer
semantic objects.

对齐关系是**推理产物**,不是名字硬匹配:EntityAligner 把知识空间的实体名
与语义层对象清单(含 description/aliases)喂给 LLM 做语义判断——覆盖
字面匹配够不着的映射(如 wiki 里的"销售单据" ↔ ent.order、"营收" ↔
revenue)。LLM 输出经确定性结构化校验(object_id 白名单 + entity 归属 +
confidence 截断)后,由调用方固化进 semantic_alignment 表;全景图的
aligns_to 边从表投影——图查询/渲染零 LLM 依赖。
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 单批喂给 LLM 的实体数(对象清单每批重复提供,供跨批推理)
_BATCH_SIZE = 20

_DESC_MAX = 160


def _loads(raw: Any) -> Any:
    """LLM 返回解析:截掉偶尔出现的 markdown 代码围栏后 json.loads。"""
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3]
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
    return raw


class EntityAligner:
    """知识实体 ↔ 硬层语义对象的 LLM 语义对齐 runner。

    LLM 只产候选;对象 id 白名单校验/实体归属校验由本类代码完成——
    与提案侧"quote 子串校验"同哲学:LLM 可能幻觉,固化前必过确定性
    校验闸门。LLM 未配置时 align 返回空且 last_error 说明原因,调用方
    引导用户走手工对齐兜底。
    """

    SYSTEM_PROMPT = """你是企业语义层的实体对齐引擎。任务:判断知识文档中出
现的实体名称与语义层对象之间是否存在语义指向关系(同一业务概念的不同表述、
俗称、简称、跨语言说法,或实体明确描述该对象代表的业务事物)。

规则:
1. object_id 只能从候选对象清单中逐字复制,禁止编造或改写。
2. 只输出有把握的对齐;某实体与任何对象都无语义关联时不要输出它。
3. 每条对齐必须给出 rationale,说明语义推理依据(业务含义层面的理由,
   而非"名字相似"这类字面理由)。
4. confidence ∈ (0,1]:1.0=同一概念的不同说法,0.6~0.9=强语义指向。
5. 一个实体可以对齐多个对象,一个对象也可以被多个实体指向。

只输出 JSON 数组,不要 markdown 代码块,不要解释文字:
[{"entity_name": "知识实体名", "object_id": "对象id", "confidence": 0.9,
  "rationale": "语义推理依据"}]"""

    def __init__(self) -> None:
        self._llm_config_cache: Optional[Dict[str, str]] = None
        self.last_error: Optional[str] = None

    # -------------------------------------------------------------- LLM client
    def _get_llm_config(self) -> Optional[Dict[str, str]]:
        """与 propose.py 同源:ModelConfigCache 第一个可用模型。"""
        if self._llm_config_cache is not None:
            return self._llm_config_cache or None
        try:
            from gyra.agent.util.llm.model_config_cache import ModelConfigCache

            all_models = ModelConfigCache.get_all_models()
            if not all_models:
                self._llm_config_cache = {}
                return None
            config = ModelConfigCache.get_config(all_models[0]) or {}
            base_url = (config.get("base_url") or config.get("api_base") or "").rstrip(
                "/"
            )
            if not base_url:
                self._llm_config_cache = {}
                return None
            if "/v1" not in base_url:
                base_url += "/v1"
            self._llm_config_cache = {
                "base_url": base_url,
                "api_key": config.get("api_key", ""),
                "model": config.get("model") or all_models[0],
            }
            return self._llm_config_cache
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[ECP] alignment LLM config init failed: {e}")
            self._llm_config_cache = {}
            return None

    async def _call_llm(self, prompt: str, max_tokens: int = 4000) -> Optional[str]:
        import httpx

        self.last_error = None
        config = self._get_llm_config()
        if not config:
            self.last_error = "LLM 未配置:ModelConfigCache 无可用模型"
            return None
        headers = {"Content-Type": "application/json"}
        if config["api_key"]:
            headers["Authorization"] = f"Bearer {config['api_key']}"
        payload = {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{config['base_url']}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                choices = resp.json().get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    return text.strip() if text else None
                self.last_error = "LLM 响应无 choices(空返回)"
        except Exception as e:  # noqa: BLE001
            self.last_error = f"LLM 调用失败: {e}"
            logger.warning(f"[ECP] alignment LLM call failed: {e}")
        return None

    # ----------------------------------------------------------------- runner
    @staticmethod
    def _object_catalog(objects: List[Any]) -> str:
        """对象清单 → prompt 中的紧凑目录(id 逐字复制是白名单约束的根基)。"""
        lines = []
        for o in objects:
            payload = o.payload or {}
            aliases = ",".join(payload.get("aliases") or []) or "-"
            desc = str(payload.get("description") or "")[:_DESC_MAX]
            lines.append(
                f"- {o.id} | {o.obj_type} | {o.name} | 别名:{aliases} | {desc}"
            )
        return "\n".join(lines)

    def _validate(
        self,
        raw: Optional[str],
        entity_names: List[str],
        object_ids: set,
    ) -> List[Dict[str, Any]]:
        """结构化校验:LLM 可能幻觉——object_id 必须在白名单、entity 必须
        在本次收集的实体清单、confidence 截断到 (0,1]。"""
        data = _loads(raw)
        if not isinstance(data, list):
            if self.last_error is None and raw is not None:
                self.last_error = "LLM 输出不是 JSON 数组"
            return []
        entity_set = set(entity_names)
        out = []
        for item in data:
            if not isinstance(item, dict):
                continue
            entity_name = str(item.get("entity_name") or "").strip()
            object_id = str(item.get("object_id") or "").strip()
            if not entity_name or entity_name not in entity_set:
                continue
            if not object_id or object_id not in object_ids:
                continue
            try:
                confidence = max(0.01, min(1.0, float(item.get("confidence"))))
            except (TypeError, ValueError):
                confidence = 0.5
            out.append(
                {
                    "entity_name": entity_name,
                    "object_id": object_id,
                    "confidence": confidence,
                    "rationale": str(item.get("rationale") or "").strip(),
                }
            )
        return out

    async def align_batch(
        self, entities: List[str], objects: List[Any]
    ) -> List[Dict[str, Any]]:
        """一批实体 × 对象清单 → 校验后的对齐候选。

        objects 是语义对象 entity 列表(需 id/obj_type/name/payload 属性)。
        """
        if not entities or not objects:
            return []
        object_ids = {o.id for o in objects}
        prompt = (
            f"## 知识实体\n" + "\n".join(entities) + "\n\n"
            f"## 语义层对象\n" + self._object_catalog(objects)
        )
        raw = await self._call_llm(prompt)
        return self._validate(raw, entities, object_ids)

    async def align(
        self, entities: List[str], objects: List[Any]
    ) -> List[Dict[str, Any]]:
        """全量对齐:实体按批分组,逐批调用(对象清单每批完整提供)。"""
        out: List[Dict[str, Any]] = []
        for i in range(0, len(entities), _BATCH_SIZE):
            batch = entities[i : i + _BATCH_SIZE]
            out.extend(await self.align_batch(batch, objects))
        return out
