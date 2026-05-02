import os
import uuid
from typing import Dict, Any, Optional

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

class Composer:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        
        self.client = OpenAI(api_key=self.api_key) if HAS_OPENAI and self.api_key else None
        self.gemini_client = genai.Client(api_key=self.gemini_key) if HAS_GEMINI and self.gemini_key else None

    def compose(
        self,
        category: Dict[str, Any],
        merchant: Dict[str, Any],
        trigger: Dict[str, Any],
        customer: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Composes a message based on the 4 contexts."""
        
        kind = trigger.get("kind", "")
        payload = trigger.get("payload", {})
        
        body = ""
        cta = ""
        rationale = ""
        send_as = "vera" if not customer else "merchant_on_behalf"
        
        # Helper to extract merchant name
        m_name = merchant.get("identity", {}).get("name", "Merchant")
        owner = merchant.get("identity", {}).get("owner_first_name", "Partner")
        merchant_id = merchant.get("identity", {}).get("merchant_id", merchant.get("merchant_id", ""))
        
        # Category specific tone
        voice = category.get("voice", {}).get("tone", "")
        prefix = "Dr. " if "clinical" in voice.lower() or category.get("slug") == "dentists" else ""
        greeting = f"Hi {prefix}{owner}" if not customer else f"Hi {customer.get('identity', {}).get('first_name', 'Customer')}"

        if customer:
            # Customer facing message
            c_name = customer.get("identity", {}).get("first_name", "")
            if kind == "recall_due" or kind == "customer_lapsed_soft":
                last_visit = customer.get("visits", {}).get("last_visit", "recently")
                service = customer.get("visits", {}).get("services_received", ["visit"])[0] if customer.get("visits", {}).get("services_received") else "visit"
                
                # Active offer?
                active_offers = [o for o in merchant.get("offers", []) if o.get("status") == "active"]
                offer_text = f" We're currently offering {active_offers[0]['title']}." if active_offers else ""
                
                body = f"Hi {c_name}, it's been a while since your last {service} on {last_visit} at {m_name}.{offer_text}"
                cta = "Would you like to book another appointment?"
                rationale = "Customer due for recall. Mentioned last visit date, service, and active offer."
                
            elif kind == "appointment_tomorrow":
                time = payload.get("time", "tomorrow")
                body = f"Hi {c_name}, this is a reminder from {m_name} for your appointment {time}."
                cta = "Reply C to confirm or R to reschedule."
                rationale = "Appointment reminder to reduce no-shows."
            else:
                body = f"Hi {c_name}, hope you are doing well. This is {m_name}."
                cta = "Reply YES to hear our latest offers."
                rationale = "Generic customer outreach."
                
        else:
            # Merchant facing message
            if kind in ["research_digest", "category_research_digest_release"]:
                digest = category.get("digest", [])
                item = digest[0] if digest else {"title": "new trend", "source": "industry", "trial_number": ""}
                title = item.get('title', 'latest insight')
                source = item.get('source', 'research')
                body = f"{greeting}, a quick update: '{title}' from {source}. This could be great for {m_name}."
                cta = "Want me to draft a customer WhatsApp from this?"
                rationale = "Research digest, citing specific source and title."
                
            elif kind == "perf_spike":
                delta = merchant.get("performance", {}).get("delta_7d", {}).get("views", payload.get("increase", "a spike in views"))
                body = f"{greeting}, great news! {m_name} saw {delta} views recently."
                cta = "Want me to turn this into a quick campaign?"
                rationale = "Performance spike notification to capitalize on momentum."
                
            elif kind == "perf_dip":
                delta = merchant.get("performance", {}).get("delta_7d", {}).get("views", payload.get("drop", "a drop in views"))
                body = f"{greeting}, {m_name} had {delta} views this week. Let's fix this."
                cta = "Want me to draft a recovery post?"
                rationale = "Performance dip notification, suggesting immediate action."
                
            elif kind == "stale_posts":
                signals = merchant.get("signals", [])
                stale_signal = next((s for s in signals if "stale_posts" in s), "stale_posts:14d")
                age = stale_signal.split(":")[1] if ":" in stale_signal else "a while"
                active_offers = [o for o in merchant.get("offers", []) if o.get("status") == "active"]
                offer_text = f" about {active_offers[0]['title']}" if active_offers else ""
                body = f"{greeting}, you haven't posted in {age}. Let's send a quick update{offer_text} to keep your profile active."
                cta = "Should I draft it?"
                rationale = "Stale post reminder using specific duration and active offer."
                
            elif kind == "ctr_below_peer_median":
                m_ctr = merchant.get("performance", {}).get("ctr", "low")
                peer_ctr = category.get("peer_stats", {}).get("median_ctr", "higher")
                body = f"{greeting}, your CTR is {m_ctr}, but peers are at {peer_ctr}. We can improve your profile offer to get more clicks."
                cta = "Want me to rewrite your profile offer?"
                rationale = "CTR comparison against category median."
                
            elif kind == "festival_upcoming":
                festival = payload.get("festival", "the upcoming festival")
                body = f"{greeting}, {festival} is around the corner. Let's run a special offer for {m_name}."
                cta = "Reply YES and I'll draft the festival message."
                rationale = "Festival preparation prompt."
                
            elif kind == "weather_heatwave" or kind == "local_event":
                event = payload.get("event", payload.get("weather", "heatwave"))
                loc = merchant.get("identity", {}).get("locality", "your area")
                body = f"{greeting}, expecting {event} in {loc}. Let's run a quick targeted campaign."
                cta = "Want a 2-line customer WhatsApp?"
                rationale = f"Local event/weather ({event}) localized to {loc}."
                
            elif kind == "review_theme_emerged":
                theme = payload.get("theme", "recent feedback")
                body = f"{greeting}, a new theme emerged in reviews: '{theme}'. "
                cta = "Want me to draft the reply?"
                rationale = "Review theme prompt."
                
            elif kind == "dormant_with_vera":
                body = f"{greeting}, noticed it's been quiet. I have a quick idea to boost visits to {m_name}."
                cta = "Want one quick idea for this week?"
                rationale = "Dormant reactivation without generic check-in."
                
            elif kind == "competitor_opened":
                comp = payload.get("competitor_name", "a competitor")
                dist = payload.get("distance", "nearby")
                body = f"{greeting}, {comp} just opened {dist} away. Let's make sure {m_name} stays top of mind."
                cta = "Want me to prepare a quick counter-offer?"
                rationale = "Competitor proximity alert."
                
            elif kind == "category_trend_movement":
                trend = payload.get("trend", "a new trend")
                body = f"{greeting}, searches for {trend} are up. Let's update {m_name}'s profile."
                cta = "Want me to turn this trend into a post?"
                rationale = "Category trend."
                
            elif kind == "regulation_change":
                reg = payload.get("regulation", "a regulation change")
                body = f"{greeting}, there's an update regarding {reg}."
                cta = "Want me to summarize what changes for your clinic/store?"
                rationale = "Regulation change alert."
                
            elif kind == "milestone_reached":
                milestone = payload.get("milestone", "a new milestone")
                body = f"{greeting}, congratulations on hitting {milestone} at {m_name}!"
                cta = "Want me to draft a thank-you post?"
                rationale = "Milestone celebration."
                
            else:
                body = f"{greeting}, checking in on {m_name}."
                cta = "Want a quick idea to boost visits this week?"
                rationale = "Fallback merchant message."

        template_name = "vera_template_v1"
        
        # If LLM is available, we can refine the message
        if (self.client or self.gemini_client) and os.getenv("USE_LLM", "true").lower() == "true":
            try:
                llm_prompt = f"""
Rewrite this WhatsApp message to be natural and engaging while strictly keeping all specific numbers, names, and facts.
Original Body: {body}
Original CTA: {cta}
Voice/Tone: {voice}
Keep it very short (WhatsApp style). Do not hallucinate. Do not add fake links.
Return a valid JSON object strictly with two keys: "body" and "cta".
"""
                import json
                if self.gemini_client:
                    resp = self.gemini_client.models.generate_content(
                        model=os.getenv("MODEL_NAME", "gemini-2.5-flash"),
                        contents=llm_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0
                        )
                    )
                    llm_data = json.loads(resp.text)
                else:
                    resp = self.client.chat.completions.create(
                        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                        messages=[{"role": "user", "content": llm_prompt}],
                        temperature=0,
                        response_format={"type": "json_object"}
                    )
                    llm_data = json.loads(resp.choices[0].message.content)
                    
                body = llm_data.get("body", body)
                cta = llm_data.get("cta", cta)
            except Exception as e:
                pass # Fallback to rule-based
                
        # Handle deduplication
        suppression_key = f"{merchant_id}_{kind}_{uuid.uuid4().hex[:4]}"

        return {
            "conversation_id": f"conv_{uuid.uuid4().hex[:12]}",
            "merchant_id": merchant_id,
            "customer_id": customer.get("identity", {}).get("customer_id") if customer else None,
            "send_as": send_as,
            "trigger_id": trigger.get("id", ""),
            "template_name": template_name,
            "template_params": [body, cta],
            "body": body,
            "cta": cta,
            "suppression_key": suppression_key,
            "rationale": rationale
        }
