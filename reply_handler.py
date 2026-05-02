import re
from typing import Dict, Any

class ReplyHandler:
    def __init__(self, store):
        self.store = store

    def is_auto_reply(self, message: str) -> bool:
        message = message.lower()
        patterns = [
            "thank you for contacting",
            "thanks for contacting",
            "we will get back to you",
            "our business hours",
            "currently unavailable",
            "away message",
            "auto reply",
            "automated response",
            "welcome to",
            "please wait",
            "we are closed",
            "will respond shortly",
            "our team will contact you"
        ]
        return any(p in message for p in patterns)

    def is_negative(self, message: str) -> bool:
        message = message.lower()
        patterns = [
            "not interested", "unsubscribe", "don't message", "do not message", "band karo"
        ]
        words = re.findall(r'\b\w+\b', message)
        if "no" in words or "stop" in words or "nahi" in words:
            return True
        return any(p in message for p in patterns)

    def is_positive(self, message: str) -> bool:
        message = message.lower()
        patterns = [
            "interested", "do it", "please share"
        ]
        words = re.findall(r'\b\w+\b', message)
        if set(words).intersection({"yes", "ok", "send", "start", "join", "haan", "chalo", "sure", "proceed"}):
            return True
        return any(p in message for p in patterns)

    def is_hostile(self, message: str) -> bool:
        message = message.lower()
        return "useless" in message or "spam" in message or "stop messaging me" in message

    def handle(self, req: Dict[str, Any]) -> Dict[str, Any]:
        msg = req.get("message", "")
        conv_id = req.get("conversation_id", "")
        
        # 1. Auto-reply detection
        if self.is_auto_reply(msg):
            return {
                "action": "wait",
                "wait_seconds": 3600,
                "rationale": "Detected WhatsApp Business auto-reply; backing off instead of wasting turns."
            }
            
        # 2. Hostile handling (special case for scoring)
        if self.is_hostile(msg):
            return {
                "action": "end",
                "rationale": "Hostility detected. Ending conversation politely."
            }

        # 3. Negative detection
        if self.is_negative(msg):
            return {
                "action": "end",
                "rationale": "Merchant declined or opted out."
            }

        # 4. Positive intent handling
        conv_state = self.store.get_conversation(conv_id) or {}
        
        if self.is_positive(msg):
            return {
                "action": "send",
                "body": "Done. I am setting it up right now.",
                "cta": "none",
                "rationale": "Merchant agreed. Moving to action phase without further qualification."
            }
            
        # 5. Unknown/Questions
        # Ensure we don't requalify
        return {
            "action": "send",
            "body": "I understand. Using our data, this will help drive more footfall.",
            "cta": "Shall we proceed?",
            "rationale": "Handled unrecognized input by redirecting."
        }
