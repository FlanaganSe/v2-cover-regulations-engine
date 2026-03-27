"""SQLAlchemy models for parcel-related tables.

Minimal models — the spatial join query uses raw SQL via text().
These exist for type safety and potential ORM use in search.
"""

from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ain: Mapped[str] = mapped_column(String(10), nullable=False)
    apn: Mapped[str | None] = mapped_column(String(12))
    address: Mapped[str | None] = mapped_column(Text)
    situs_city: Mapped[str | None] = mapped_column(String(50))
    situs_zip: Mapped[str | None] = mapped_column(String(10))
    use_code: Mapped[str | None] = mapped_column(String(10))
    use_description: Mapped[str | None] = mapped_column(Text)
    year_built: Mapped[int | None] = mapped_column(Integer)
    bedrooms: Mapped[int | None] = mapped_column(Integer)
    sqft_main: Mapped[int | None] = mapped_column(Integer)
    land_value: Mapped[float | None] = mapped_column(Numeric)
    improvement_value: Mapped[float | None] = mapped_column(Numeric)
    center_lat: Mapped[float | None] = mapped_column()
    center_lon: Mapped[float | None] = mapped_column()
    geom = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)


__all__ = ["Base", "Parcel"]
