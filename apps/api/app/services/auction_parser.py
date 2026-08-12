import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

MINECRAFT_FORMATTING = re.compile(r"§.")
NON_WORD = re.compile(r"[^a-z0-9]+")
ENCHANTMENT = re.compile(r"\b([A-Za-z][A-Za-z ]{2,30})\s+([IVX]+)\b")


def clean_minecraft_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    without_formatting = MINECRAFT_FORMATTING.sub("", value)
    return " ".join(without_formatting.replace("\u00a0", " ").split())


def normalized_item_id(item_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", item_name).encode("ascii", "ignore").decode()
    slug = NON_WORD.sub("-", normalized.lower()).strip("-")
    return slug[:160] or "unknown-item"


def _timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _fingerprint(
    *, item_name: str, category: str, tier: str, extra: str, lore: str
) -> dict[str, Any]:
    enchantments = [
        f"{name.strip().lower()} {level}"
        for name, level in ENCHANTMENT.findall(lore)
        if name.strip().lower() not in {"health", "defense", "damage", "strength"}
    ]
    stars = max(lore.count("✪"), len(re.findall(r"\b\d+\s*star", lore, re.I)))
    return {
        "name": item_name,
        "category": category,
        "tier": tier,
        "extra": extra,
        "enchantments": sorted(set(enchantments)),
        "stars": stars,
        "recombobulated": "recombobulated" in lore.lower(),
    }


def parse_auction(raw: Any) -> dict[str, Any] | None:
    """Normalize one Hypixel auction into a persistable BIN record.

    The public feed contains both bids and BINs. SkyFlip intentionally uses BINs for
    comparable pricing because an active bid is not an executable purchase price.
    """

    if not isinstance(raw, dict) or not bool(raw.get("bin")) or bool(raw.get("claimed")):
        return None
    auction_uuid = str(raw.get("uuid", "")).strip()
    item_name = clean_minecraft_text(raw.get("item_name"))
    if not auction_uuid or not item_name:
        return None
    try:
        price = float(raw.get("starting_bid", 0))
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    category = clean_minecraft_text(raw.get("category")).lower() or "misc"
    tier = clean_minecraft_text(raw.get("tier")).upper() or "COMMON"
    lore = clean_minecraft_text(raw.get("item_lore"))
    extra = clean_minecraft_text(raw.get("extra"))
    fingerprint = _fingerprint(
        item_name=item_name,
        category=category,
        tier=tier,
        extra=extra,
        lore=lore,
    )
    fingerprint_hash = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "auction_uuid": auction_uuid,
        "item_uuid": str(raw["item_uuid"]) if raw.get("item_uuid") else None,
        "item_name": item_name,
        "normalized_item_id": normalized_item_id(item_name),
        "fingerprint_hash": fingerprint_hash,
        "item_fingerprint": fingerprint,
        "item_lore": lore or None,
        "extra": extra or None,
        "category": category,
        "tier": tier,
        "price": price,
        "is_bin": True,
        "is_claimed": False,
        "start_at": _timestamp(raw.get("start")),
        "end_at": _timestamp(raw.get("end")),
    }
