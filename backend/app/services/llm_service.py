"""LLM assessment service — OpenAI Responses API with structured output.

The LLM explains deterministic facts in plain English. It does not decide
confidence, compute FAR, or invent numbers. If the LLM is unavailable,
a template-based deterministic fallback is returned.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.schemas.parcel import Assessment

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.data.zone_rules import AduRules, ZoneRule
    from app.schemas.parcel import Overlays, ParcelFacts
    from app.services.rules_engine import Confidence, ParsedZone

_ZONING_SUMMARY_URL = "https://planning.lacity.gov/zoning/summary-of-zoning-regulations"
_ZA_MEMO_143_URL = "https://planning.lacity.gov/resources/za-memos"


# ── Internal LLM output schema ──────────────────────────────────


class _AssessmentLLMOutput(BaseModel):
    """Schema sent to OpenAI structured output. Separate from public API."""

    summary: str
    citations: list[str]
    caveats: list[str]


# ── Prompt builders ──────────────────────────────────────────────


def build_system_prompt(
    zone_rule: ZoneRule | None,
    confidence_level: str,
    confidence_reasons: tuple[str, ...],
) -> str:
    """Build the system prompt with zone rules and grounding instructions."""
    lines = [
        "You are a zoning analyst explaining development standards for a "
        "residential parcel in Los Angeles.",
        "",
        "RULES:",
        "- Only cite LAMC sections and URLs listed below.",
        "- Only state facts provided in the user message. Do not invent numbers.",
        "- Do not recalculate FAR, setbacks, or height. Restate them in plain English.",
        "- The confidence level is already computed. Explain it; do not change it.",
        "- If overlays or flags apply, say 'additional restrictions may apply' — "
        "do not guess what those restrictions are.",
        "- This is not legal advice.",
        "",
    ]

    if zone_rule:
        lines.append(f"ZONE: {zone_rule.zone_class} (LAMC §{zone_rule.lamc_section})")
        lines.append(f"  Min lot area: {zone_rule.min_lot_area_sqft:,} sqft")
        height = (
            f"{zone_rule.max_height_ft} ft" if zone_rule.max_height_ft else "No limit"
        )
        stories = str(zone_rule.max_stories) if zone_rule.max_stories else "No limit"
        lines.append(f"  Max height: {height} / {stories} stories")
        lines.append(f"  {zone_rule.far_type}: {zone_rule.far_or_rfa}")
        lines.append(f"  Front setback: {zone_rule.front_setback_ft} ft")
        lines.append(f"  Side setback: {zone_rule.side_setback_ft} ft")
        lines.append(f"  Rear setback: {zone_rule.rear_setback_ft} ft")
        lines.append(f"  Density: {zone_rule.density_description}")
        lines.append(f"  Allowed uses: {', '.join(zone_rule.allowed_uses)}")
        lines.append("")

    lines.append(f"CONFIDENCE: {confidence_level}")
    if confidence_reasons:
        for reason in confidence_reasons:
            lines.append(f"  - {reason}")
    lines.append("")

    lines.append("CITATION WHITELIST:")
    if zone_rule:
        lines.append(f"  - LAMC §{zone_rule.lamc_section}")
        if zone_rule.source_url:
            lines.append(f"  - {zone_rule.source_url}")
    lines.append(f"  - {_ZONING_SUMMARY_URL}")
    lines.append(f"  - {_ZA_MEMO_143_URL}")

    return "\n".join(lines)


def build_user_message(
    parcel: ParcelFacts,
    parsed_zone: ParsedZone,
    zone_rule: ZoneRule | None,
    confidence: Confidence,
    overlays: Overlays,
    adu: AduRules,
    effective_far: float | None,
) -> str:
    """Build the user message as structured JSON with all deterministic facts."""
    data: dict[str, object] = {
        "parcel": {
            "address": parcel.address,
            "lot_sqft": parcel.lot_sqft,
            "year_built": parcel.year_built,
            "use": parcel.use_description,
        },
        "zone": {
            "zone_string": parsed_zone.raw,
            "zone_class": parsed_zone.zone_class,
            "height_district": parsed_zone.height_district,
            "q_flag": parsed_zone.q_flag,
            "t_flag": parsed_zone.t_flag,
            "d_flag": parsed_zone.d_flag,
            "suffixes": list(parsed_zone.suffixes),
            "is_chapter_1a": parsed_zone.is_chapter_1a,
        },
        "standards": {
            "height_ft": zone_rule.max_height_ft if zone_rule else None,
            "stories": zone_rule.max_stories if zone_rule else None,
            "far_or_rfa": effective_far,
            "far_type": zone_rule.far_type if zone_rule else None,
            "front_setback_ft": zone_rule.front_setback_ft if zone_rule else None,
            "side_setback_ft": zone_rule.side_setback_ft if zone_rule else None,
            "rear_setback_ft": zone_rule.rear_setback_ft if zone_rule else None,
            "density": zone_rule.density_description if zone_rule else None,
            "allowed_uses": list(zone_rule.allowed_uses) if zone_rule else [],
        },
        "overlays": {
            "specific_plan": (
                overlays.specific_plan.name if overlays.specific_plan else None
            ),
            "hpoz": overlays.hpoz.name if overlays.hpoz else None,
            "community_plan": overlays.community_plan,
            "general_plan_lu": overlays.general_plan_lu,
        },
        "adu": {
            "allowed": adu.allowed,
            "max_sqft": adu.max_sqft,
            "notes": adu.notes,
        },
        "confidence": {
            "level": confidence.level,
            "reasons": list(confidence.reasons),
        },
    }
    return json.dumps(data)


# ── Deterministic fallback ───────────────────────────────────────


def build_fallback_assessment(
    parsed_zone: ParsedZone,
    zone_rule: ZoneRule | None,
    confidence: Confidence,
    adu: AduRules,
    effective_far: float | None,
) -> Assessment:
    """Build a template-based assessment when the LLM is unavailable."""
    parts: list[str] = []

    if parsed_zone.zone_class and zone_rule:
        parts.append(
            f"This parcel is zoned {parsed_zone.raw} ({zone_rule.zone_class})."
        )
        height = (
            f"{zone_rule.max_height_ft} ft"
            if zone_rule.max_height_ft
            else "no height limit"
        )
        stories = (
            f"{zone_rule.max_stories} stories"
            if zone_rule.max_stories
            else "no story limit"
        )
        parts.append(f"Maximum height: {height} / {stories}.")
        if effective_far is not None:
            parts.append(f"Floor area: {effective_far} {zone_rule.far_type}.")
        parts.append(f"Front setback: {zone_rule.front_setback_ft} ft.")
    elif parsed_zone.is_chapter_1a:
        parts.append(
            f"This parcel is in a Chapter 1A zone ({parsed_zone.raw}). "
            "Development standards are not yet supported."
        )
    else:
        parts.append(
            f"Zone string '{parsed_zone.raw}' could not be mapped to "
            "a supported residential zone."
        )

    if adu.allowed:
        parts.append(f"ADU likely allowed (up to {adu.max_sqft:,} sqft).")

    parts.append(f"Confidence: {confidence.level}.")

    citations: list[str] = []
    if zone_rule:
        citations.append(f"LAMC §{zone_rule.lamc_section}")
        if zone_rule.source_url:
            citations.append(zone_rule.source_url)
    citations.append(_ZONING_SUMMARY_URL)

    caveats = [
        "AI-generated summary unavailable — showing deterministic assessment only.",
        (
            "This is an automated assessment for informational purposes only. "
            "Consult the LA Department of Building and Safety for official "
            "determinations."
        ),
    ]

    return Assessment(
        summary=" ".join(parts),
        citations=citations,
        caveats=caveats,
        llm_available=False,
    )


# ── Main entry point ─────────────────────────────────────────────


async def generate_assessment(
    parcel: ParcelFacts,
    parsed_zone: ParsedZone,
    zone_rule: ZoneRule | None,
    confidence: Confidence,
    overlays: Overlays,
    adu: AduRules,
    effective_far: float | None,
) -> Assessment:
    """Generate an LLM assessment, falling back to deterministic if unavailable."""
    if not settings.openai_api_key.strip():
        return build_fallback_assessment(
            parsed_zone, zone_rule, confidence, adu, effective_far
        )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        system_prompt = build_system_prompt(
            zone_rule, confidence.level, confidence.reasons
        )
        user_message = build_user_message(
            parcel, parsed_zone, zone_rule, confidence, overlays, adu, effective_far
        )

        response = await client.responses.parse(
            model=settings.openai_model,
            instructions=system_prompt,
            input=user_message,
            text_format=_AssessmentLLMOutput,
            temperature=0.2,
            max_output_tokens=600,
        )

        parsed = response.output_parsed
        if parsed is None:
            return build_fallback_assessment(
                parsed_zone, zone_rule, confidence, adu, effective_far
            )

        # Filter citations to whitelist only
        allowed_citations: set[str] = {
            _ZONING_SUMMARY_URL,
            _ZA_MEMO_143_URL,
        }
        if zone_rule:
            allowed_citations.add(f"LAMC §{zone_rule.lamc_section}")
            if zone_rule.source_url:
                allowed_citations.add(zone_rule.source_url)
        citations = [c for c in parsed.citations if c in allowed_citations]

        # Ensure the legal caveat is always present
        caveats = list(parsed.caveats)
        legal_caveat = (
            "This is an automated assessment for informational "
            "purposes only. Consult the LA Department of Building "
            "and Safety for official determinations."
        )
        if not any("informational purposes" in c for c in caveats):
            caveats.append(legal_caveat)

        return Assessment(
            summary=parsed.summary,
            citations=citations,
            caveats=caveats,
            llm_available=True,
        )
    except Exception:
        logger.warning(
            "LLM assessment failed, using fallback",
            exc_info=True,
        )
        return build_fallback_assessment(
            parsed_zone, zone_rule, confidence, adu, effective_far
        )


__all__ = [
    "build_fallback_assessment",
    "build_system_prompt",
    "build_user_message",
    "generate_assessment",
]
