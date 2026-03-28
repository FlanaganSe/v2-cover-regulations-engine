"""API tests for homepage metadata endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.schemas.home import FeaturedParcel, HomeMetadata, HomeSource


async def _dummy_session() -> AsyncGenerator[object, None]:
    yield object()


def test_home_endpoint_returns_homepage_metadata() -> None:
    client = TestClient(app)
    response_model = HomeMetadata(
        data_as_of=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        supported_zone_classes=["R1", "R2"],
        sources=[
            HomeSource(
                id="parcels",
                label="LA County Parcels",
                source_url="https://example.com/parcels",
                coverage_note="Parcel coverage note.",
            )
        ],
        featured_parcels=[
            FeaturedParcel(
                category="clean_supported",
                label="Clean supported parcel",
                description="A straightforward supported example.",
                ain="1234567890",
                apn="1234-567-890",
                address="123 Main St",
                zone_class="R1",
            )
        ],
    )

    app.dependency_overrides[get_session] = _dummy_session

    try:
        with patch(
            "app.routers.home.get_home_metadata",
            AsyncMock(return_value=response_model),
        ):
            response = client.get("/api/home")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["supported_zone_classes"] == ["R1", "R2"]
    assert body["sources"][0]["id"] == "parcels"
    assert body["featured_parcels"][0]["category"] == "clean_supported"
