from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List, Optional
from datetime import datetime

class ContextPayload(BaseModel):
    scope: Literal["category", "merchant", "customer", "trigger"]
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: str

class ContextResponseAccepted(BaseModel):
    accepted: Literal[True]
    ack_id: str
    stored_at: str

class ContextResponseStale(BaseModel):
    accepted: Literal[False]
    reason: Literal["stale_version"]
    current_version: int

class TickRequest(BaseModel):
    now: str
    available_triggers: List[str]

class ActionModel(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: Literal["vera", "merchant_on_behalf"]
    trigger_id: str
    template_name: str
    template_params: List[str]
    body: str
    cta: str
    suppression_key: str
    rationale: str

class TickResponse(BaseModel):
    actions: List[ActionModel]

class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    from_role: Literal["merchant", "customer"]
    message: str
    received_at: str
    turn_number: int

class ReplyResponseSend(BaseModel):
    action: Literal["send"]
    body: str
    cta: str
    rationale: str

class ReplyResponseWait(BaseModel):
    action: Literal["wait"]
    wait_seconds: int
    rationale: str

class ReplyResponseEnd(BaseModel):
    action: Literal["end"]
    rationale: str

class ComposeDebugRequest(BaseModel):
    category_id: str
    merchant_id: str
    trigger_id: str
    customer_id: Optional[str] = None
