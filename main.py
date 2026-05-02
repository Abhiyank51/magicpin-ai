import os
import time
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from models import (
    ContextPayload, ContextResponseAccepted, ContextResponseStale,
    TickRequest, TickResponse, ActionModel,
    ReplyRequest, ReplyResponseSend, ReplyResponseWait, ReplyResponseEnd,
    ComposeDebugRequest
)
from context_store import ContextStore
from composer import Composer
from reply_handler import ReplyHandler
import dataset_loader

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vera.main")

app = FastAPI(title="Magicpin Vera Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# Global Services
store = ContextStore()
composer = Composer()
reply_handler = ReplyHandler(store)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Vera Bot. Loading dataset...")
    counts = dataset_loader.load_all(store)
    logger.info(f"Loaded contexts: {counts}")

# -------------------------------------------------------------------
# CHALLENGE ENDPOINTS
# -------------------------------------------------------------------

@app.get("/v1/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": store.get_counts()
    }

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Abhiyank Magicpin Vera Bot",
        "team_members": ["Abhiyank Yadav"],
        "model": "rule-based + optional LLM composer",
        "approach": "stateful FastAPI bot using 4-context composition, trigger prioritization, category-aware templates, multi-turn reply handling, and dashboard-driven endpoint testing",
        "contact_email": os.getenv("CONTACT_EMAIL", "test@example.com"),
        "version": "1.0.0",
        "submitted_at": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/v1/context")
async def push_context(req: ContextPayload):
    try:
        status, data = store.upsert(req.scope, req.context_id, req.version, req.payload)
        
        if status == "accepted":
            return ContextResponseAccepted(
                accepted=True,
                ack_id=data["ack_id"],
                stored_at=data["stored_at"]
            )
        elif status == "stale_version":
            return JSONResponse(
                status_code=409,
                content={
                    "accepted": False,
                    "reason": "stale_version",
                    "current_version": data
                }
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid scope")
    except Exception as e:
        logger.error(f"Context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/tick", response_model=TickResponse)
async def tick(req: TickRequest):
    actions = []
    seen_merchants = set()
    
    for trigger_id in req.available_triggers:
        trigger = store.get("trigger", trigger_id)
        if not trigger:
            logger.warning(f"Trigger {trigger_id} not found, skipping.")
            continue
            
        merchant_id = trigger.get("merchant_id") or trigger.get("payload", {}).get("merchant_id")
        if not merchant_id:
            logger.warning(f"Trigger {trigger_id} missing merchant_id, skipping.")
            continue
            
        # Optional: prioritize or dedup triggers per merchant in a single tick
        if merchant_id in seen_merchants:
            continue
            
        merchant = store.get("merchant", merchant_id)
        if not merchant:
            logger.warning(f"Merchant {merchant_id} not found, skipping.")
            continue
            
        category_slug = merchant.get("category_slug")
        category = store.get("category", category_slug)
        if not category:
            logger.warning(f"Category {category_slug} not found, skipping.")
            continue
            
        customer_id = trigger.get("customer_id")
        customer = store.get("customer", customer_id) if customer_id else None
        
        try:
            action_dict = composer.compose(category, merchant, trigger, customer)
            actions.append(ActionModel(**action_dict))
            seen_merchants.add(merchant_id)
            
            # Save conversation state
            store.save_conversation(
                action_dict["conversation_id"],
                {
                    "merchant_id": merchant_id,
                    "customer_id": customer_id,
                    "trigger_id": trigger_id,
                    "suppression_key": action_dict["suppression_key"]
                }
            )
            
        except Exception as e:
            logger.error(f"Error composing action for {trigger_id}: {e}")
            continue

    return TickResponse(actions=actions)

@app.post("/v1/reply")
async def reply(req: ReplyRequest):
    try:
        req_dict = req.dict()
        action_dict = reply_handler.handle(req_dict)
        
        # Save updated conversation state
        store.save_conversation(
            req.conversation_id,
            {
                "last_action": action_dict["action"],
                "turn_count": req.turn_number
            }
        )
        
        if action_dict["action"] == "send":
            return ReplyResponseSend(**action_dict)
        elif action_dict["action"] == "wait":
            return ReplyResponseWait(**action_dict)
        else:
            return ReplyResponseEnd(**action_dict)
    except Exception as e:
        logger.error(f"Reply error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# DEBUG ENDPOINTS
# -------------------------------------------------------------------

@app.get("/debug/contexts")
async def debug_contexts_counts():
    return store.get_counts()

@app.get("/debug/contexts/{scope}")
async def debug_contexts_scope(scope: str):
    if scope not in ["category", "merchant", "customer", "trigger"]:
        raise HTTPException(status_code=400, detail="Invalid scope")
    return store.get_all(scope)

@app.get("/debug/contexts/{scope}/{context_id}")
async def debug_contexts_single(scope: str, context_id: str):
    data = store.get(scope, context_id)
    if not data:
        raise HTTPException(status_code=404, detail="Not found")
    return data

@app.get("/debug/triggers")
async def debug_triggers():
    return list(store.get_all("trigger").keys())

@app.get("/debug/sample-payloads")
async def debug_sample_payloads():
    return dataset_loader.get_sample_payloads()

@app.post("/debug/compose")
async def debug_compose(req: ComposeDebugRequest):
    cat = store.get("category", req.category_id)
    mer = store.get("merchant", req.merchant_id)
    trg = store.get("trigger", req.trigger_id)
    cus = store.get("customer", req.customer_id) if req.customer_id else None
    
    if not cat or not mer or not trg:
        raise HTTPException(status_code=400, detail="Missing required context")
        
    try:
        return composer.compose(cat, mer, trg, cus)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# The frontend should now be run separately (e.g., via Vercel or npm run dev)
@app.get("/")
async def root():
    return {"message": "Magicpin Vera Bot API is running. Access the frontend dashboard separately."}
