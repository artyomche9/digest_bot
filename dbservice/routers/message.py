from decimal import Decimal

from Enum import SortingType  # TODO: return to common
from models import Message
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException

router = APIRouter()


@router.post("/")
async def insert_messages(messages: List[Message]):
    raise HTTPException(status_code=500, detail="Method not implemented")


@router.put("/")
async def upsert_messages(messages: List[Message]):
    raise HTTPException(status_code=500, detail="Method not implemented")


@router.get("/linkless", response_model=List[Message])
async def get_linkless_messages():
    raise HTTPException(status_code=500, detail="Method not implemented")


@router.patch("/links")
async def update_message_links(messages: List[Message]):
    raise HTTPException(status_code=500, detail="Method not implemented")


@router.get("/top", response_model=List[Message])
async def get_top_messages(
        after_ts: Decimal,
        channel_id: Optional[str] = None,
        category_name: Optional[str] = None,
        user_id: Optional[str] = None,
        sorting_type: SortingType = SortingType.REPLIES,
        top_count: int = Query(default=10, ge=1),
):
    raise HTTPException(status_code=500, detail="Method not implemented")


def get_top_messages_empty(
        after_ts: Decimal,
        sorting_type: SortingType = SortingType.REPLIES,
        top_count: int = 10,
) -> List[Message]:
    raise NotImplementedError


def get_top_messages_by_channel_id(
        channel_id: str,
        after_ts: Decimal,
        sorting_type: SortingType = SortingType.REPLIES,
        top_count: int = 10,
) -> List[Message]:
    raise NotImplementedError


def get_top_messages_by_category_name(
        category_name: str,
        after_ts: Decimal,
        sorting_type: SortingType = SortingType.REPLIES,
        top_count: int = 10,
        user_id: Optional[str] = None,
) -> List[Message]:
    raise NotImplementedError