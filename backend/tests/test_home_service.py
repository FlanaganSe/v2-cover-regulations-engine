"""Tests for homepage metadata service."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.home import FeaturedParcel
from app.services.home_service import get_home_metadata


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _IterableResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def __iter__(self) -> Iterator[object]:
        return iter(self._rows)


@pytest.mark.asyncio
async def test_get_home_metadata_builds_sources_and_featured_parcels() -> None:
    session = AsyncMock()
    data_as_of = datetime(2026, 3, 27, 12, 0, tzinfo=UTC)
    session.execute.side_effect = [
        _ScalarResult(data_as_of),
        _IterableResult(
            [
                SimpleNamespace(
                    table_name="parcels",
                    source_url="https://example.com/parcels",
                ),
                SimpleNamespace(
                    table_name="buildings",
                    source_url="https://example.com/buildings",
                ),
            ]
        ),
    ]

    featured = [
        FeaturedParcel(
            category="clean_supported",
            label="Clean supported parcel",
            description="A straightforward supported example.",
            ain="1234567890",
            apn="1234-567-890",
            address="123 Main St",
            zone_class="R1",
        )
    ]

    with patch(
        "app.services.home_service._collect_featured_parcels",
        AsyncMock(return_value=featured),
    ):
        metadata = await get_home_metadata(session)

    assert metadata.data_as_of == data_as_of
    assert metadata.supported_zone_classes == sorted(metadata.supported_zone_classes)
    assert metadata.sources[0].id == "parcels"
    assert metadata.sources[0].source_url == "https://example.com/parcels"
    assert "demo neighborhoods" in metadata.sources[-1].coverage_note
    assert metadata.featured_parcels[0].ain == "1234567890"


@pytest.mark.asyncio
async def test_get_home_metadata_handles_missing_provenance() -> None:
    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(None),
        _IterableResult([]),
    ]

    with patch(
        "app.services.home_service._collect_featured_parcels",
        AsyncMock(return_value=[]),
    ):
        metadata = await get_home_metadata(session)

    assert metadata.data_as_of is None
    assert metadata.featured_parcels == []
    assert all(source.source_url is None for source in metadata.sources)
    assert any(source.id == "buildings" for source in metadata.sources)
