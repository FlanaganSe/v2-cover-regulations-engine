"""Tests for LLM assessment service: fallback, prompt construction, mock API."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.data.zone_rules import AduRules, ZoneRule, get_adu_rules
from app.schemas.parcel import Assessment, OverlayRef, Overlays, ParcelFacts
from app.services.llm_service import (
    _AssessmentLLMOutput,
    build_fallback_assessment,
    build_system_prompt,
    build_user_message,
    generate_assessment,
)
from app.services.rules_engine import (
    Confidence,
    ParsedZone,
    compute_confidence,
    lookup_zone_rule,
    parse_zone_string,
)

# ── Fixtures ─────────────────────────────────────────────────────


def _r1_parsed() -> ParsedZone:
    return parse_zone_string("R1-1")


def _r1_rule() -> ZoneRule:
    rule = lookup_zone_rule("R1")
    assert rule is not None
    return rule


def _r1_confidence() -> Confidence:
    return compute_confidence(_r1_parsed(), _r1_rule())


def _parcel_facts() -> ParcelFacts:
    return ParcelFacts(
        ain="5432001001",
        apn="5432-001-001",
        address="123 MAIN ST",
        center_lat=34.05,
        center_lon=-118.25,
        lot_sqft=6000.0,
        year_built=1955,
        use_description="Single Family Residence",
        bedrooms=3,
        sqft_main=1500,
    )


def _overlays_empty() -> Overlays:
    return Overlays()


def _overlays_with_hpoz() -> Overlays:
    return Overlays(hpoz=OverlayRef(name="Angelino Heights"))


def _adu_r1() -> AduRules:
    return get_adu_rules("R1")


# ── Fallback tests ───────────────────────────────────────────────


class TestFallbackAssessment:
    def test_returns_llm_unavailable(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert isinstance(result, Assessment)
        assert not result.llm_available

    def test_summary_contains_zone_class(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert "R1" in result.summary

    def test_summary_contains_height(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert "33 ft" in result.summary

    def test_summary_contains_far(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert "0.45" in result.summary
        assert "RFA" in result.summary

    def test_summary_contains_adu(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert "ADU" in result.summary

    def test_summary_contains_confidence(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert "Confidence: High" in result.summary

    def test_citations_include_lamc_section(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert any("12.08" in c for c in result.citations)

    def test_caveats_mention_deterministic(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert any("deterministic" in c for c in result.caveats)

    def test_caveats_mention_not_legal_advice(self) -> None:
        result = build_fallback_assessment(
            _r1_parsed(), _r1_rule(), _r1_confidence(), _adu_r1(), 0.45
        )
        assert any("informational purposes" in c for c in result.caveats)

    def test_chapter_1a_fallback(self) -> None:
        parsed = parse_zone_string("[MB3-SH1-1]")
        result = build_fallback_assessment(
            parsed, None, Confidence("Low", ("Chapter 1A",)), _adu_r1(), None
        )
        assert "Chapter 1A" in result.summary

    def test_unsupported_zone_fallback(self) -> None:
        parsed = parse_zone_string("CM-1")
        result = build_fallback_assessment(
            parsed, None, Confidence("Low", ("Unsupported",)), _adu_r1(), None
        )
        assert "could not be mapped" in result.summary

    def test_unlimited_height(self) -> None:
        """R4 has no height limit — fallback should say so."""
        parsed = parse_zone_string("R4-1")
        rule = lookup_zone_rule("R4")
        assert rule is not None
        conf = compute_confidence(parsed, rule)
        result = build_fallback_assessment(parsed, rule, conf, get_adu_rules("R4"), 3.0)
        assert "no height limit" in result.summary


# ── Prompt construction tests ────────────────────────────────────


class TestBuildSystemPrompt:
    def test_includes_lamc_section(self) -> None:
        prompt = build_system_prompt(_r1_rule(), "High", ("No modifiers",))
        assert "12.08" in prompt

    def test_includes_grounding_rules(self) -> None:
        prompt = build_system_prompt(_r1_rule(), "High", ("No modifiers",))
        assert "Do not invent numbers" in prompt

    def test_includes_citation_whitelist(self) -> None:
        prompt = build_system_prompt(_r1_rule(), "High", ("No modifiers",))
        assert "CITATION WHITELIST" in prompt
        assert "planning.lacity.gov" in prompt

    def test_includes_confidence_level(self) -> None:
        prompt = build_system_prompt(_r1_rule(), "Medium", ("Q flag",))
        assert "CONFIDENCE: Medium" in prompt
        assert "Q flag" in prompt

    def test_none_zone_rule(self) -> None:
        prompt = build_system_prompt(None, "Low", ("Unsupported",))
        assert "ZONE:" not in prompt
        assert "CONFIDENCE: Low" in prompt

    def test_zone_details_present(self) -> None:
        prompt = build_system_prompt(_r1_rule(), "High", ())
        assert "5,000 sqft" in prompt
        assert "33 ft" in prompt
        assert "0.45" in prompt


class TestBuildUserMessage:
    def test_valid_json(self) -> None:
        msg = build_user_message(
            _parcel_facts(),
            _r1_parsed(),
            _r1_rule(),
            _r1_confidence(),
            _overlays_empty(),
            _adu_r1(),
            0.45,
        )
        data = json.loads(msg)
        assert "parcel" in data
        assert "zone" in data
        assert "standards" in data

    def test_includes_parcel_address(self) -> None:
        msg = build_user_message(
            _parcel_facts(),
            _r1_parsed(),
            _r1_rule(),
            _r1_confidence(),
            _overlays_empty(),
            _adu_r1(),
            0.45,
        )
        data = json.loads(msg)
        assert data["parcel"]["address"] == "123 MAIN ST"

    def test_includes_overlay_info(self) -> None:
        msg = build_user_message(
            _parcel_facts(),
            _r1_parsed(),
            _r1_rule(),
            _r1_confidence(),
            _overlays_with_hpoz(),
            _adu_r1(),
            0.45,
        )
        data = json.loads(msg)
        assert data["overlays"]["hpoz"] == "Angelino Heights"

    def test_includes_confidence(self) -> None:
        msg = build_user_message(
            _parcel_facts(),
            _r1_parsed(),
            _r1_rule(),
            _r1_confidence(),
            _overlays_empty(),
            _adu_r1(),
            0.45,
        )
        data = json.loads(msg)
        assert data["confidence"]["level"] == "High"


# ── generate_assessment tests ────────────────────────────────────


@pytest.mark.asyncio
class TestGenerateAssessment:
    async def test_no_api_key_returns_fallback(self) -> None:
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )
        assert not result.llm_available
        assert "R1" in result.summary

    async def test_api_exception_returns_fallback(self) -> None:
        mock_client = AsyncMock()
        mock_client.responses.parse.side_effect = RuntimeError("timeout")

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_model = "gpt-4.1-mini"
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )
        assert not result.llm_available

    async def test_successful_api_call(self) -> None:
        llm_output = _AssessmentLLMOutput(
            summary="This R1-zoned parcel allows a single-family home.",
            citations=["LAMC §12.08"],
            caveats=["Not legal advice."],
        )
        mock_response = AsyncMock()
        mock_response.output_parsed = llm_output

        mock_client = AsyncMock()
        mock_client.responses.parse.return_value = mock_response

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_model = "gpt-4.1-mini"
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )

        assert result.llm_available
        assert "R1" in result.summary
        assert "LAMC §12.08" in result.citations

    async def test_refusal_returns_fallback(self) -> None:
        """Model refusal (output_parsed=None) → fallback."""
        mock_response = AsyncMock()
        mock_response.output_parsed = None

        mock_client = AsyncMock()
        mock_client.responses.parse.return_value = mock_response

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_model = "gpt-4.1-mini"
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )

        assert not result.llm_available

    async def test_legal_caveat_always_present(self) -> None:
        """Even if LLM omits it, the legal caveat is appended."""
        llm_output = _AssessmentLLMOutput(
            summary="Zoning summary.",
            citations=["LAMC §12.08"],
            caveats=[],  # LLM returned no caveats
        )
        mock_response = AsyncMock()
        mock_response.output_parsed = llm_output

        mock_client = AsyncMock()
        mock_client.responses.parse.return_value = mock_response

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_model = "gpt-4.1-mini"
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )

        assert result.llm_available
        assert any("informational purposes" in c for c in result.caveats)

    async def test_whitespace_api_key_returns_fallback(self) -> None:
        """Whitespace-only API key should be treated as empty."""
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.openai_api_key = "   "
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )
        assert not result.llm_available

    async def test_hallucinated_citations_filtered(self) -> None:
        """Citations not in the whitelist are stripped."""
        llm_output = _AssessmentLLMOutput(
            summary="Zoning summary.",
            citations=[
                "LAMC §12.08",
                "https://fake-url.com/hallucinated",
            ],
            caveats=[],
        )
        mock_response = AsyncMock()
        mock_response.output_parsed = llm_output

        mock_client = AsyncMock()
        mock_client.responses.parse.return_value = mock_response

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncOpenAI",
                return_value=mock_client,
            ),
        ):
            mock_settings.openai_api_key = "sk-test"
            mock_settings.openai_model = "gpt-4.1-mini"
            result = await generate_assessment(
                _parcel_facts(),
                _r1_parsed(),
                _r1_rule(),
                _r1_confidence(),
                _overlays_empty(),
                _adu_r1(),
                0.45,
            )

        assert result.llm_available
        assert "LAMC §12.08" in result.citations
        assert "https://fake-url.com/hallucinated" not in result.citations
