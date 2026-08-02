import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter()
get_bearer_token = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


@router.post("/v2/gyra/reasoning_engine", dependencies=[])
async def gyra_plan():
    pass


@router.post("/v2/gyra/memory/write", dependencies=[])
async def gyra_memory_write():
    logger.info(f"gyra_memory_write:{1},{2}")


@router.post("/v2/gyra/memory/read", dependencies=[])
async def gyra_memory_read():
    logger.info(f"gyra_memory_write:{1},{2}")
