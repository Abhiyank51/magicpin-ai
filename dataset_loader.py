"""
dataset_loader.py — Load local dataset JSON files into the context store at startup.

Loads:
  dataset/categories/*.json          → scope="category",  key=slug
  dataset/merchants_seed.json        → scope="merchant",  key=merchant_id
  dataset/customers_seed.json        → scope="customer",  key=customer_id
  dataset/triggers_seed.json         → scope="trigger",   key=id
"""

from __future__ import annotations
import json
import logging
from pathlib import Path

logger = logging.getLogger("vera.dataset_loader")

DATASET_DIR = Path(__file__).parent / "dataset"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_all(store) -> dict:
    """
    Load all seed data into *store* (ContextStore instance).
    Returns summary counts dict.
    """
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}

    if not DATASET_DIR.exists():
        logger.warning("dataset/ directory not found — skipping seed load.")
        return counts

    # ── Categories ────────────────────────────────────────────────────────
    cat_dir = DATASET_DIR / "categories"
    if cat_dir.exists():
        for f in sorted(cat_dir.glob("*.json")):
            try:
                data = _load_json(f)
                slug = data.get("slug", f.stem)
                result, _ = store.upsert("category", slug, 1, data)
                if result == "accepted":
                    counts["category"] += 1
                    logger.info("Category loaded: %s", slug)
            except Exception as e:
                logger.error("Failed to load category %s: %s", f.name, e)
    else:
        logger.warning("dataset/categories/ not found.")

    # ── Merchants ──────────────────────────────────────────────────────────
    merchants_path = DATASET_DIR / "merchants_seed.json"
    if merchants_path.exists():
        try:
            data = _load_json(merchants_path)
            items = data.get("merchants", [])
            for m in items:
                mid = m.get("merchant_id")
                if not mid:
                    continue
                result, _ = store.upsert("merchant", mid, 1, m)
                if result == "accepted":
                    counts["merchant"] += 1
            logger.info("Merchants loaded: %d", counts["merchant"])
        except Exception as e:
            logger.error("Failed to load merchants: %s", e)
    else:
        logger.warning("merchants_seed.json not found.")

    # ── Customers ──────────────────────────────────────────────────────────
    customers_path = DATASET_DIR / "customers_seed.json"
    if customers_path.exists():
        try:
            data = _load_json(customers_path)
            items = data.get("customers", [])
            for c in items:
                cid = c.get("customer_id")
                if not cid:
                    continue
                result, _ = store.upsert("customer", cid, 1, c)
                if result == "accepted":
                    counts["customer"] += 1
            logger.info("Customers loaded: %d", counts["customer"])
        except Exception as e:
            logger.error("Failed to load customers: %s", e)
    else:
        logger.warning("customers_seed.json not found.")

    # ── Triggers ───────────────────────────────────────────────────────────
    triggers_path = DATASET_DIR / "triggers_seed.json"
    if triggers_path.exists():
        try:
            data = _load_json(triggers_path)
            items = data.get("triggers", [])
            for t in items:
                tid = t.get("id")
                if not tid:
                    continue
                result, _ = store.upsert("trigger", tid, 1, t)
                if result == "accepted":
                    counts["trigger"] += 1
            logger.info("Triggers loaded: %d", counts["trigger"])
        except Exception as e:
            logger.error("Failed to load triggers: %s", e)
    else:
        logger.warning("triggers_seed.json not found.")

    logger.info("Dataset load complete: %s", counts)
    return counts


def get_sample_payloads() -> dict:
    """Return sample payloads for dashboard forms."""
    samples = {}

    # Category sample
    cat_dir = DATASET_DIR / "categories"
    if cat_dir.exists():
        for f in cat_dir.glob("*.json"):
            try:
                samples["category"] = _load_json(f)
                break
            except Exception:
                pass

    # Merchant sample
    mp = DATASET_DIR / "merchants_seed.json"
    if mp.exists():
        try:
            data = _load_json(mp)
            items = data.get("merchants", [])
            if items:
                samples["merchant"] = items[0]
        except Exception:
            pass

    # Customer sample
    cp = DATASET_DIR / "customers_seed.json"
    if cp.exists():
        try:
            data = _load_json(cp)
            items = data.get("customers", [])
            if items:
                samples["customer"] = items[0]
        except Exception:
            pass

    # Trigger sample
    tp = DATASET_DIR / "triggers_seed.json"
    if tp.exists():
        try:
            data = _load_json(tp)
            items = data.get("triggers", [])
            if items:
                samples["trigger"] = items[0]
        except Exception:
            pass

    return samples
