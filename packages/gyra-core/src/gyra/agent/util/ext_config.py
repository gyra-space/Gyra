from typing import Dict, Optional

from gyra._private.pydantic import BaseModel


class ExtConfigHolder(BaseModel):
    ext_config: Optional[Dict] = None
