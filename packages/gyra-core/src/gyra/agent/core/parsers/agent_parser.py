from typing import Optional, Any, List, Type

from gyra.agent import Action, Resource
from gyra.agent.core.parsers.tool_parser import ToolParser
from gyra.agent.resource.app import AppResource


class AgentParser(ToolParser):

    @property
    def resource_types(self) -> List[Type[Resource]]:
        return [AppResource]

    async def _resources_to_functions(self, all_resources: Resource) -> Optional[List[dict]]:
        return await super()._resources_to_functions(all_resources)

    async def _resources_to_prompt(self, all_resources: Resource) -> Optional[List[dict]]:
        return await super()._resources_to_prompt(all_resources)


