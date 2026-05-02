import threading
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import uuid

class ContextStore:
    def __init__(self):
        self._lock = threading.RLock()
        # Storage format: scope -> id -> {"version": int, "payload": dict, "delivered_at": str}
        self.store: Dict[str, Dict[str, Dict[str, Any]]] = {
            "category": {},
            "merchant": {},
            "customer": {},
            "trigger": {}
        }
        self.conversations: Dict[str, Dict[str, Any]] = {}
        
    def upsert(self, scope: str, context_id: str, version: int, payload: dict) -> Tuple[str, Any]:
        with self._lock:
            if scope not in self.store:
                return "invalid_scope", None
                
            scope_store = self.store[scope]
            existing = scope_store.get(context_id)
            
            if existing:
                if version == existing["version"]:
                    return "accepted", {"ack_id": f"ack_{uuid.uuid4().hex[:8]}", "stored_at": datetime.utcnow().isoformat() + "Z"}
                elif version < existing["version"]:
                    return "stale_version", existing["version"]
                    
            # Update or create
            scope_store[context_id] = {
                "version": version,
                "payload": payload,
                "delivered_at": datetime.utcnow().isoformat() + "Z"
            }
            return "accepted", {"ack_id": f"ack_{uuid.uuid4().hex[:8]}", "stored_at": datetime.utcnow().isoformat() + "Z"}

    def get(self, scope: str, context_id: str) -> Optional[dict]:
        with self._lock:
            if scope not in self.store:
                return None
            item = self.store[scope].get(context_id)
            return item["payload"] if item else None

    def get_all(self, scope: str) -> dict:
        with self._lock:
            if scope not in self.store:
                return {}
            return {k: v["payload"] for k, v in self.store[scope].items()}

    def get_counts(self) -> dict:
        with self._lock:
            return {
                "category": len(self.store["category"]),
                "merchant": len(self.store["merchant"]),
                "customer": len(self.store["customer"]),
                "trigger": len(self.store["trigger"])
            }
            
    def get_conversation(self, conv_id: str) -> Optional[dict]:
        with self._lock:
            return self.conversations.get(conv_id)
            
    def save_conversation(self, conv_id: str, data: dict):
        with self._lock:
            if conv_id not in self.conversations:
                self.conversations[conv_id] = {
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "turn_count": 0,
                    "status": "active"
                }
            self.conversations[conv_id].update(data)
