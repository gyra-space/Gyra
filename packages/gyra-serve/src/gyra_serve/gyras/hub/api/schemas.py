# Define your Pydantic schemas here
from typing import Any, Dict, Optional

from gyra._private.pydantic import BaseModel, ConfigDict, Field, model_to_dict

from ..config import SERVE_APP_NAME_HUMP


class ServeRequest(BaseModel):
    """GyrasHub request model"""

    id: Optional[int] = Field(None, description="id")
    name: Optional[str] = Field(None, description="Gyras name")
    type: Optional[str] = Field(None, description="Gyras type")
    version: Optional[str] = Field(None, description="Gyras version")
    description: Optional[str] = Field(None, description="Gyras description")
    author: Optional[str] = Field(None, description="Gyras author")
    email: Optional[str] = Field(None, description="Gyras email")
    storage_channel: Optional[str] = Field(None, description="Gyras storage channel")
    storage_url: Optional[str] = Field(None, description="Gyras storage url")
    download_param: Optional[str] = Field(None, description="Gyras download param")
    installed: Optional[int] = Field(None, description="Gyras installed")

    model_config = ConfigDict(title=f"ServeRequest for {SERVE_APP_NAME_HUMP}")

    def to_dict(self, **kwargs) -> Dict[str, Any]:
        """Convert the model to a dictionary"""
        return model_to_dict(self, **kwargs)


class ServerResponse(ServeRequest):
    gmt_created: Optional[str] = Field(None, description="Gyras create time")
    gmt_modified: Optional[str] = Field(None, description="Gyras upload time")
