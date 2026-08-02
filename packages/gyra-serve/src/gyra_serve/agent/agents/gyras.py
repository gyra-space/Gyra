from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GyrasMessage:
    sender: str
    receiver: str
    content: str
    action_report: str

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> GyrasMessage:
        return GyrasMessage(
            sender=d["sender"],
            receiver=d["receiver"],
            content=d["content"],
            model_name=d["model_name"],
            agent_name=d["agent_name"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class GyrasTaskStep:
    task_num: str
    task_content: str
    state: str
    result: str
    agent_name: str
    model_name: str

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> GyrasTaskStep:
        return GyrasTaskStep(
            task_num=d["task_num"],
            task_content=d["task_content"],
            state=d["state"],
            result=d["result"],
            agent_name=d["agent_name"],
            model_name=d["model_name"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class GyrasCompletion:
    conv_id: str
    task_steps: Optional[List[GyrasTaskStep]]
    messages: Optional[List[GyrasMessage]]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> GyrasCompletion:
        return GyrasCompletion(
            conv_id=d.get("conv_id"),
            task_steps=GyrasTaskStep.from_dict(d["task_steps"]),
            messages=GyrasMessage.from_dict(d["messages"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)
