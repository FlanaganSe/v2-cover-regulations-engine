"""Tests for zone string parser, rule lookup, and confidence computation."""

from app.data.zone_rules import (
    HEIGHT_DISTRICT_FAR,
    ZONE_RULES,
    get_adu_rules,
)
from app.services.rules_engine import (
    compute_confidence,
    get_effective_far,
    lookup_zone_rule,
    parse_zone_string,
)

# ── Zone string parser ──────────────────────────────────────────


class TestParseZoneString:
    def test_clean_r1(self) -> None:
        p = parse_zone_string("R1-1")
        assert p.zone_class == "R1"
        assert p.height_district == "1"
        assert not p.q_flag
        assert not p.t_flag
        assert not p.d_flag
        assert p.suffixes == ()

    def test_q_bracket(self) -> None:
        p = parse_zone_string("[Q]R1-1")
        assert p.zone_class == "R1"
        assert p.q_flag
        assert not p.t_flag

    def test_q_paren(self) -> None:
        p = parse_zone_string("(Q)R1-1")
        assert p.zone_class == "R1"
        assert p.q_flag

    def test_t_and_q(self) -> None:
        p = parse_zone_string("(T)(Q)RD1.5-1")
        assert p.zone_class == "RD1.5"
        assert p.q_flag
        assert p.t_flag
        assert p.height_district == "1"

    def test_d_flag(self) -> None:
        p = parse_zone_string("R1-1D")
        assert p.zone_class == "R1"
        assert p.d_flag
        assert p.height_district == "1"

    def test_hpoz_suffix(self) -> None:
        p = parse_zone_string("R1-1-HPOZ")
        assert p.zone_class == "R1"
        assert p.suffixes == ("HPOZ",)

    def test_multiple_suffixes(self) -> None:
        p = parse_zone_string("[Q]R1-2D-CDO-RIO")
        assert p.zone_class == "R1"
        assert p.height_district == "2"
        assert p.q_flag
        assert p.d_flag
        assert p.suffixes == ("CDO", "RIO")

    def test_height_district_1l(self) -> None:
        p = parse_zone_string("R1-1L")
        assert p.zone_class == "R1"
        assert p.height_district == "1L"

    def test_height_district_1vl(self) -> None:
        p = parse_zone_string("R3-1VL")
        assert p.zone_class == "R3"
        assert p.height_district == "1VL"

    def test_re9(self) -> None:
        p = parse_zone_string("RE9-1")
        assert p.zone_class == "RE9"
        assert p.height_district == "1"

    def test_rd1_5(self) -> None:
        p = parse_zone_string("RD1.5-1")
        assert p.zone_class == "RD1.5"

    def test_r1_variation_zone(self) -> None:
        p = parse_zone_string("R1V1-1")
        assert p.zone_class == "R1V1"

    def test_rs(self) -> None:
        p = parse_zone_string("RS-1")
        assert p.zone_class == "RS"

    def test_chapter_1a_bracket(self) -> None:
        p = parse_zone_string("[MB3-SH1-1]")
        assert p.is_chapter_1a
        assert p.zone_class is None

    def test_chapter_1a_community_plan(self) -> None:
        p = parse_zone_string("R1-1", community_plan="Central City")
        assert p.is_chapter_1a
        assert p.zone_class is None

    def test_non_residential(self) -> None:
        p = parse_zone_string("CM-1-CUGU")
        assert p.zone_class == "CM"

    def test_f_prefix_paren(self) -> None:
        p = parse_zone_string("(F)CM-1-CUGU")
        assert p.zone_class == "CM"

    def test_f_prefix_bracket_not_chapter_1a(self) -> None:
        p = parse_zone_string("[F]R1-1")
        assert not p.is_chapter_1a
        assert p.zone_class == "R1"

    def test_empty_string(self) -> None:
        p = parse_zone_string("")
        assert p.zone_class is None
        assert not p.is_chapter_1a

    def test_none_input(self) -> None:
        p = parse_zone_string(None)
        assert p.zone_class is None

    def test_garbage_string(self) -> None:
        p = parse_zone_string("NOT-A-ZONE!!!")
        assert p.zone_class is None

    def test_ra_zone(self) -> None:
        p = parse_zone_string("RA-1")
        assert p.zone_class == "RA"

    def test_r5_zone(self) -> None:
        p = parse_zone_string("R5-2")
        assert p.zone_class == "R5"
        assert p.height_district == "2"


# ── Rule lookup ──────────────────────────────────────────────────


class TestLookupZoneRule:
    def test_all_14_zones(self) -> None:
        for zone_class in ZONE_RULES:
            rule = lookup_zone_rule(zone_class)
            assert rule is not None
            assert rule.zone_class == zone_class

    def test_unknown_zone(self) -> None:
        assert lookup_zone_rule("XYZ") is None

    def test_none_input(self) -> None:
        assert lookup_zone_rule(None) is None

    def test_r1_variation(self) -> None:
        rule = lookup_zone_rule("R1V1")
        assert rule is not None
        assert rule.zone_class == "R1"

    def test_r1_height(self) -> None:
        rule = lookup_zone_rule("R1")
        assert rule is not None
        assert rule.max_height_ft == 33
        assert rule.max_stories == 2

    def test_r4_unlimited_height(self) -> None:
        rule = lookup_zone_rule("R4")
        assert rule is not None
        assert rule.max_height_ft is None


class TestHeightDistrictFar:
    def test_hd1(self) -> None:
        assert HEIGHT_DISTRICT_FAR["1"] == 3.0

    def test_hd1l(self) -> None:
        assert HEIGHT_DISTRICT_FAR["1L"] == 3.0

    def test_hd2(self) -> None:
        assert HEIGHT_DISTRICT_FAR["2"] == 6.0

    def test_hd3(self) -> None:
        assert HEIGHT_DISTRICT_FAR["3"] == 10.0

    def test_hd4(self) -> None:
        assert HEIGHT_DISTRICT_FAR["4"] == 13.0


class TestEffectiveFar:
    def test_rfa_zone_ignores_hd(self) -> None:
        rule = lookup_zone_rule("R1")
        far = get_effective_far("R1", "2", rule)
        assert far == 0.45  # RFA, not HD 2's 6.0

    def test_far_zone_uses_hd(self) -> None:
        rule = lookup_zone_rule("R3")
        far = get_effective_far("R3", "2", rule)
        assert far == 6.0  # HD 2

    def test_unknown_hd_falls_back(self) -> None:
        rule = lookup_zone_rule("R3")
        far = get_effective_far("R3", "99", rule)
        assert far == 3.0  # Fallback to zone rule default


# ── Confidence computation ───────────────────────────────────────


class TestConfidence:
    def test_clean_r1_high(self) -> None:
        parsed = parse_zone_string("R1-1")
        rule = lookup_zone_rule("R1")
        c = compute_confidence(parsed, rule)
        assert c.level == "High"

    def test_q_flag_medium(self) -> None:
        parsed = parse_zone_string("(Q)R1-1")
        rule = lookup_zone_rule("R1")
        c = compute_confidence(parsed, rule)
        assert c.level == "Medium"
        assert any("Qualified" in r for r in c.reasons)

    def test_hpoz_overlay_low(self) -> None:
        parsed = parse_zone_string("R1-1")
        rule = lookup_zone_rule("R1")
        c = compute_confidence(parsed, rule, hpoz_name="Angelino Heights")
        assert c.level == "Low"

    def test_unsupported_zone_low(self) -> None:
        parsed = parse_zone_string("CM-1")
        rule = lookup_zone_rule("CM")
        c = compute_confidence(parsed, rule)
        assert c.level == "Low"

    def test_chapter_1a_low(self) -> None:
        parsed = parse_zone_string("[MB3-SH1-1]")
        c = compute_confidence(parsed, None)
        assert c.level == "Low"
        assert any("Chapter 1A" in r for r in c.reasons)

    def test_specific_plan_medium(self) -> None:
        parsed = parse_zone_string("R1-1")
        rule = lookup_zone_rule("R1")
        c = compute_confidence(parsed, rule, specific_plan_name="Vermont/Western")
        assert c.level == "Medium"

    def test_d_flag_medium(self) -> None:
        parsed = parse_zone_string("R1-1D")
        rule = lookup_zone_rule("R1")
        c = compute_confidence(parsed, rule)
        assert c.level == "Medium"
        assert any("D limitation" in r for r in c.reasons)

    def test_r1_variation_medium(self) -> None:
        parsed = parse_zone_string("R1V1-1")
        rule = lookup_zone_rule("R1V1")
        c = compute_confidence(parsed, rule)
        assert c.level == "Medium"
        assert any("R1 variation" in r for r in c.reasons)

    def test_multiple_flags_low(self) -> None:
        parsed = parse_zone_string("(T)(Q)R1-1D")
        rule = lookup_zone_rule("R1")
        c = compute_confidence(parsed, rule)
        assert c.level == "Low"


# ── ADU rules ────────────────────────────────────────────────────


class TestAduRules:
    def test_single_family_zone(self) -> None:
        adu = get_adu_rules("R1")
        assert adu.allowed
        assert adu.max_sqft == 1200
        assert adu.setbacks_ft == 4

    def test_multi_family_zone(self) -> None:
        adu = get_adu_rules("R3")
        assert adu.allowed

    def test_unknown_zone(self) -> None:
        adu = get_adu_rules("XYZ")
        assert not adu.allowed
