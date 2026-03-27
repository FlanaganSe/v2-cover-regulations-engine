"""Zone string parser, rule pack lookup, and confidence computation.

Pure functions — no database or I/O dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.zone_rules import (
    CHAPTER_1A_CPA,
    HEIGHT_DISTRICT_FAR,
    RFA_ZONES,
    ZONE_RULES,
    AduRules,
    ZoneRule,
    get_adu_rules,
)

# ---------------------------------------------------------------------------
# Zone string parser
# ---------------------------------------------------------------------------

# Matches patterns like: (T)(Q)R1-1D-CDO-RIO, [Q]RD1.5-2, R1-1-HPOZ
_PREFIX_PATTERN = re.compile(r"[\(\[](F|Q|T)[\)\]]", re.IGNORECASE)

_ZONE_BODY = re.compile(
    r"^"
    r"((?:[\(\[][FQTÜ]+[\)\]]\s*)*)"  # all prefix flags (consumed separately)
    r"([A-Z][A-Z0-9.]+?)"  # base zone class
    r"-"
    r"(\d+(?:XL|VL|L)?)"  # height district (1, 1L, 1VL, 1XL, 2..)
    r"(D)?"  # D limitation
    r"((?:-[A-Z][A-Z0-9]*)*)"  # dash-separated suffixes
    r"$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedZone:
    """Structured result of zone string parsing."""

    zone_class: str | None  # None if unparseable
    height_district: str
    q_flag: bool
    t_flag: bool
    d_flag: bool
    suffixes: tuple[str, ...]
    raw: str
    is_chapter_1a: bool = False


def parse_zone_string(
    zone_cmplt: str | None,
    *,
    community_plan: str | None = None,
) -> ParsedZone:
    """Parse a ZONE_CMPLT string into structured components.

    Returns a ParsedZone with zone_class=None if the string cannot be parsed.
    Chapter 1A is detected via bracket format or community plan area name.
    """
    if not zone_cmplt:
        return ParsedZone(
            zone_class=None,
            height_district="",
            q_flag=False,
            t_flag=False,
            d_flag=False,
            suffixes=(),
            raw=zone_cmplt or "",
        )

    raw = zone_cmplt.strip()

    # Chapter 1A detection: bracket-enclosed format like [MB3-SH1-1]
    # Known single-letter bracket prefixes are NOT Chapter 1A
    _KNOWN_BRACKET = re.compile(r"^\[[FQT]\]", re.IGNORECASE)
    chapter_1a = raw.startswith("[") and not _KNOWN_BRACKET.match(raw)
    if not chapter_1a and community_plan:
        chapter_1a = community_plan.strip() in CHAPTER_1A_CPA

    if chapter_1a:
        return ParsedZone(
            zone_class=None,
            height_district="",
            q_flag=False,
            t_flag=False,
            d_flag=False,
            suffixes=(),
            raw=raw,
            is_chapter_1a=True,
        )

    # Extract prefix flags
    prefix_flags = {m.group(1).upper() for m in _PREFIX_PATTERN.finditer(raw)}
    q_flag = "Q" in prefix_flags
    t_flag = "T" in prefix_flags

    # Strip all prefix groups for body parsing
    body = _PREFIX_PATTERN.sub("", raw).strip()

    match = _ZONE_BODY.match(body)
    if not match:
        return ParsedZone(
            zone_class=None,
            height_district="",
            q_flag=q_flag,
            t_flag=t_flag,
            d_flag=False,
            suffixes=(),
            raw=raw,
        )

    (
        _prefix_in_body,
        zone_class,
        height_district,
        d_flag_str,
        suffixes_str,
    ) = match.groups()

    zone_class = zone_class.upper()
    height_district = height_district.upper()
    d_flag = d_flag_str is not None

    suffixes: tuple[str, ...] = ()
    if suffixes_str:
        suffixes = tuple(s.upper() for s in suffixes_str.split("-") if s)

    return ParsedZone(
        zone_class=zone_class,
        height_district=height_district,
        q_flag=q_flag,
        t_flag=t_flag,
        d_flag=d_flag,
        suffixes=suffixes,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Rule lookup
# ---------------------------------------------------------------------------


def lookup_zone_rule(zone_class: str | None) -> ZoneRule | None:
    """Look up development standards for a zone class. Returns None if unknown."""
    if zone_class is None:
        return None
    # Handle R1 variation zones (R1V1, R1V2, R1R, R1H, etc.)
    is_r1_variant = (
        zone_class.startswith("R1")
        and zone_class != "R1"
        and zone_class not in ZONE_RULES
    )
    if is_r1_variant:
        return ZONE_RULES.get("R1")
    return ZONE_RULES.get(zone_class)


def get_effective_far(
    zone_class: str | None,
    height_district: str,
    zone_rule: ZoneRule | None,
) -> float | None:
    """Compute the effective FAR/RFA for a parcel.

    RFA zones use the zone rule's RFA value (ignores height district).
    FAR zones use height district FAR.
    """
    if zone_rule is None or zone_class is None:
        return None
    if zone_class in RFA_ZONES:
        return zone_rule.far_or_rfa
    return HEIGHT_DISTRICT_FAR.get(height_district, zone_rule.far_or_rfa)


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------

_OVERLAY_SUFFIXES = frozenset({"HPOZ", "CDO", "RFA", "CPIO", "RIO", "NSO", "POD", "SN"})


@dataclass(frozen=True)
class Confidence:
    """Deterministic confidence assessment."""

    level: str  # "High", "Medium", "Low"
    reasons: tuple[str, ...]


def compute_confidence(
    parsed: ParsedZone,
    zone_rule: ZoneRule | None,
    *,
    specific_plan_name: str | None = None,
    hpoz_name: str | None = None,
) -> Confidence:
    """Compute confidence level and reasons deterministically."""
    reasons: list[str] = []

    # Chapter 1A → Low
    if parsed.is_chapter_1a:
        reasons.append("Downtown / Chapter 1A zone — not yet supported")
        return Confidence(level="Low", reasons=tuple(reasons))

    # Unsupported zone → Low
    if parsed.zone_class is None:
        reasons.append("Zone string could not be parsed")
        return Confidence(level="Low", reasons=tuple(reasons))

    if zone_rule is None:
        reasons.append(
            f"Zone class '{parsed.zone_class}' is not in the curated rule set"
        )
        return Confidence(level="Low", reasons=tuple(reasons))

    # HPOZ → Low (design review required)
    if hpoz_name:
        reasons.append(
            f"In HPOZ '{hpoz_name}' — design review required for new construction"
        )

    # Specific plan → Medium
    if specific_plan_name:
        reasons.append(
            f"In Specific Plan '{specific_plan_name}' — additional standards may apply"
        )

    # Q flag
    if parsed.q_flag:
        reasons.append("Qualified (Q) conditions may impose additional restrictions")

    # T flag
    if parsed.t_flag:
        reasons.append("Tentative (T) classification — zone may change")

    # D limitation
    if parsed.d_flag:
        reasons.append("D limitation — reduced FAR may apply")

    # Overlay suffixes
    overlay_hits = _OVERLAY_SUFFIXES & set(parsed.suffixes)
    for suffix in sorted(overlay_hits):
        if suffix == "HPOZ" and hpoz_name:
            continue  # Already flagged above
        reasons.append(f"-{suffix} suffix — additional standards may apply")

    # R1 variation zones
    if (
        parsed.zone_class is not None
        and parsed.zone_class.startswith("R1")
        and parsed.zone_class != "R1"
    ):
        reasons.append(
            f"R1 variation zone ({parsed.zone_class}) — reduced RFA may apply"
        )

    # Determine level
    if not reasons:
        return Confidence(
            level="High",
            reasons=("Supported residential zone with no modifiers",),
        )

    if hpoz_name:
        return Confidence(level="Low", reasons=tuple(reasons))

    if len(reasons) >= 3:
        return Confidence(level="Low", reasons=tuple(reasons))

    return Confidence(level="Medium", reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# Combined assessment helpers
# ---------------------------------------------------------------------------


def get_adu_assessment(zone_class: str | None) -> AduRules:
    """Get ADU assessment for a zone class."""
    if zone_class is None:
        return get_adu_rules("")
    return get_adu_rules(zone_class)


__all__ = [
    "Confidence",
    "ParsedZone",
    "compute_confidence",
    "get_adu_assessment",
    "get_effective_far",
    "lookup_zone_rule",
    "parse_zone_string",
]
