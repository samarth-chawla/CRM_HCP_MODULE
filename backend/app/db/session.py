"""Database engine, session factory, and schema bootstrap."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import models

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and seed reference data if empty."""
    # Import models so they register on Base.metadata before create_all.
    import app.db.models  # noqa: F401

    models.Base.metadata.create_all(bind=engine)
    _seed_approved_materials()
    _seed_demo_hcps()


def _seed_approved_materials() -> None:
    from app.db.models import ApprovedMaterial

    defaults = [
        ("Clinical study brochure", "Efficacy"),
        ("Safety profile PDF", "Safety"),
        ("Product detail aid", "Overview"),
        ("Patient subgroup analysis", "Efficacy"),
        ("Dosing guide", "Safety"),
    ]
    with SessionLocal() as db:
        existing = db.query(ApprovedMaterial).count()
        if existing:
            return
        for name, category in defaults:
            db.add(ApprovedMaterial(id=_slug(name), name=name, category=category))
        db.commit()


def _seed_demo_hcps() -> None:
    from app.db.models import HCP

    with SessionLocal() as db:
        if db.query(HCP).count():
            return
        demo = [
            HCP(
                id="HCP-1001",
                name="Dr. Priya Sharma",
                specialty="Cardiology",
                territory="West",
                preferred_channel="Email",
                previous_product_interest="Product X",
            ),
            HCP(
                id="HCP-1002",
                name="Dr. Mehta",
                specialty="Endocrinology",
                territory="North",
                preferred_channel="Field visit",
                previous_product_interest="Product Y",
            ),
        ]
        db.add_all(demo)
        db.commit()


def _slug(name: str) -> str:
    return "MAT-" + "".join(ch if ch.isalnum() else "-" for ch in name).upper()
