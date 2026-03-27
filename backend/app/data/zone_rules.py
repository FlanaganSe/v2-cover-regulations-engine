"""Hardcoded rule pack for LA City residential zone classes.

Hand-curated from LA City Zoning Code Summary PDF and ZA Memo 143.
Covers ~14 residential zones (~95% of residential parcels).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ZoneRule:
    """Development standards for a single residential zone class."""

    zone_class: str
    lamc_section: str
    min_lot_area_sqft: int
    max_height_ft: int | None  # None = unlimited (R4, R5)
    max_stories: int | None  # None = no story limit
    far_or_rfa: float
    far_type: str  # "RFA" or "FAR"
    front_setback_ft: str  # May include formula like "20%≤25"
    side_setback_ft: str  # May include formula like "5+1/st"
    rear_setback_ft: str  # May include formula like "15+1/st"
    density_description: str
    allowed_uses: tuple[str, ...] = field(default_factory=tuple)
    source_url: str = ""


# Residential zone rules keyed by zone class
ZONE_RULES: dict[str, ZoneRule] = {
    "RA": ZoneRule(
        zone_class="RA",
        lamc_section="12.07",
        min_lot_area_sqft=17_500,
        max_height_ft=36,
        max_stories=2,
        far_or_rfa=0.25,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="10",
        rear_setback_ft="25%≤25",
        density_description="1 per lot",
        allowed_uses=("Single-family", "Agriculture", "ADU"),
    ),
    "RE40": ZoneRule(
        zone_class="RE40",
        lamc_section="12.07.01",
        min_lot_area_sqft=40_000,
        max_height_ft=36,
        max_stories=2,
        far_or_rfa=0.25,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="10",
        rear_setback_ft="25%≤25",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "RE20": ZoneRule(
        zone_class="RE20",
        lamc_section="12.07.01",
        min_lot_area_sqft=20_000,
        max_height_ft=36,
        max_stories=2,
        far_or_rfa=0.35,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="10",
        rear_setback_ft="25%≤25",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "RE15": ZoneRule(
        zone_class="RE15",
        lamc_section="12.07.01",
        min_lot_area_sqft=15_000,
        max_height_ft=36,
        max_stories=2,
        far_or_rfa=0.35,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="10%w",
        rear_setback_ft="25%≤25",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "RE11": ZoneRule(
        zone_class="RE11",
        lamc_section="12.07.01",
        min_lot_area_sqft=11_000,
        max_height_ft=33,
        max_stories=2,
        far_or_rfa=0.40,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="5",
        rear_setback_ft="20%≤25",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "RE9": ZoneRule(
        zone_class="RE9",
        lamc_section="12.07.01",
        min_lot_area_sqft=9_000,
        max_height_ft=33,
        max_stories=2,
        far_or_rfa=0.40,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="5",
        rear_setback_ft="20%≤25",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "RS": ZoneRule(
        zone_class="RS",
        lamc_section="12.07.1",
        min_lot_area_sqft=7_500,
        max_height_ft=33,
        max_stories=2,
        far_or_rfa=0.45,
        far_type="RFA",
        front_setback_ft="20%≤25",
        side_setback_ft="5",
        rear_setback_ft="20",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "R1": ZoneRule(
        zone_class="R1",
        lamc_section="12.08",
        min_lot_area_sqft=5_000,
        max_height_ft=33,
        max_stories=2,
        far_or_rfa=0.45,
        far_type="RFA",
        front_setback_ft="20%≤20",
        side_setback_ft="5",
        rear_setback_ft="15",
        density_description="1 per lot",
        allowed_uses=("Single-family", "ADU"),
    ),
    "R2": ZoneRule(
        zone_class="R2",
        lamc_section="12.09",
        min_lot_area_sqft=5_000,
        max_height_ft=33,
        max_stories=2,
        far_or_rfa=0.45,
        far_type="RFA",
        front_setback_ft="20%≤20",
        side_setback_ft="5",
        rear_setback_ft="15",
        density_description="1 unit per 2,500 sqft",
        allowed_uses=("Two-family", "ADU"),
    ),
    "RD3": ZoneRule(
        zone_class="RD3",
        lamc_section="12.09.1",
        min_lot_area_sqft=3_000,
        max_height_ft=45,
        max_stories=None,
        far_or_rfa=3.0,
        far_type="FAR",
        front_setback_ft="15",
        side_setback_ft="5",
        rear_setback_ft="15",
        density_description="1 unit per 3,000 sqft",
        allowed_uses=("Multi-family", "ADU"),
    ),
    "RD2": ZoneRule(
        zone_class="RD2",
        lamc_section="12.09.1",
        min_lot_area_sqft=2_000,
        max_height_ft=45,
        max_stories=None,
        far_or_rfa=3.0,
        far_type="FAR",
        front_setback_ft="15",
        side_setback_ft="5",
        rear_setback_ft="15",
        density_description="1 unit per 2,000 sqft",
        allowed_uses=("Multi-family", "ADU"),
    ),
    "RD1.5": ZoneRule(
        zone_class="RD1.5",
        lamc_section="12.09.1",
        min_lot_area_sqft=1_500,
        max_height_ft=45,
        max_stories=None,
        far_or_rfa=3.0,
        far_type="FAR",
        front_setback_ft="15",
        side_setback_ft="5",
        rear_setback_ft="15",
        density_description="1 unit per 1,500 sqft",
        allowed_uses=("Multi-family", "ADU"),
    ),
    "R3": ZoneRule(
        zone_class="R3",
        lamc_section="12.10",
        min_lot_area_sqft=5_000,
        max_height_ft=45,
        max_stories=3,
        far_or_rfa=3.0,
        far_type="FAR",
        front_setback_ft="15",
        side_setback_ft="5+1/st",
        rear_setback_ft="15+1/st",
        density_description="1 unit per 800 sqft",
        allowed_uses=("Multi-family", "ADU"),
    ),
    "R4": ZoneRule(
        zone_class="R4",
        lamc_section="12.11",
        min_lot_area_sqft=5_000,
        max_height_ft=None,
        max_stories=None,
        far_or_rfa=3.0,
        far_type="FAR",
        front_setback_ft="15",
        side_setback_ft="5+1/st",
        rear_setback_ft="15+1/st",
        density_description="1 unit per 400 sqft",
        allowed_uses=("Multi-family", "Hotel", "ADU"),
    ),
    "R5": ZoneRule(
        zone_class="R5",
        lamc_section="12.12",
        min_lot_area_sqft=5_000,
        max_height_ft=None,
        max_stories=None,
        far_or_rfa=3.0,
        far_type="FAR",
        front_setback_ft="15",
        side_setback_ft="5+1/st",
        rear_setback_ft="15+1/st",
        density_description="1 unit per 200 sqft",
        allowed_uses=("Multi-family", "Hotel", "ADU"),
    ),
}

# Height district → FAR mapping
# For RFA zones (R1/RS/RE/RA), RFA overrides this.
# For FAR zones (RD/R3/R4/R5), this is the binding constraint.
HEIGHT_DISTRICT_FAR: dict[str, float] = {
    "1": 3.0,
    "1L": 3.0,
    "1VL": 3.0,
    "1XL": 3.0,
    "2": 6.0,
    "3": 10.0,
    "4": 13.0,
}

# Zones that use RFA (Residential Floor Area) instead of standard FAR
RFA_ZONES: frozenset[str] = frozenset(
    {"RA", "RE40", "RE20", "RE15", "RE11", "RE9", "RS", "R1", "R2"}
)

# Known Chapter 1A zone prefixes (Downtown)
CHAPTER_1A_CPA: frozenset[str] = frozenset({"Central City", "Central City North"})


@dataclass(frozen=True)
class AduRules:
    """ADU/JADU assessment per ZA Memo 143."""

    allowed: bool
    max_sqft: int
    setbacks_ft: int
    notes: str


def get_adu_rules(zone_class: str) -> AduRules:
    """Return ADU assessment for a given zone class."""
    single_family_zones = {"RA", "RE40", "RE20", "RE15", "RE11", "RE9", "RS", "R1"}
    if zone_class in single_family_zones:
        return AduRules(
            allowed=True,
            max_sqft=1200,
            setbacks_ft=4,
            notes=(
                "1 ADU (max 1,200 sqft detached) + 1 JADU (max 500 sqft interior) "
                "allowed per lot. State law (AB 68, SB 13) preempts local zoning. "
                "4 ft side/rear setbacks. No parking within 0.5 mi of transit."
            ),
        )
    if zone_class in {"R2", "RD3", "RD2", "RD1.5", "R3", "R4", "R5"}:
        return AduRules(
            allowed=True,
            max_sqft=1200,
            setbacks_ft=4,
            notes=(
                "ADU allowed on multi-family lots per state law. "
                "At least 1 detached ADU per lot. "
                "4 ft side/rear setbacks. State law preempts local zoning."
            ),
        )
    return AduRules(
        allowed=False,
        max_sqft=0,
        setbacks_ft=0,
        notes="ADU rules not assessed for this zone class.",
    )


__all__ = [
    "CHAPTER_1A_CPA",
    "HEIGHT_DISTRICT_FAR",
    "RFA_ZONES",
    "ZONE_RULES",
    "AduRules",
    "ZoneRule",
    "get_adu_rules",
]
