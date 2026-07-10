"""SQLAlchemy ORM models for the CRM HCP module.

Mirrors the schema in the requirements (section 17). Tables: users, hcps,
interactions, interaction_attendees, interaction_materials, interaction_samples,
follow_up_actions, chat_messages, audit_logs, approved_materials.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class HCP(Base):
    __tablename__ = "hcps"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    specialty: Mapped[str] = mapped_column(String(255), default="")
    territory: Mapped[str] = mapped_column(String(255), default="")
    preferred_channel: Mapped[str] = mapped_column(String(64), default="")
    previous_product_interest: Mapped[str] = mapped_column(String(255), default="")
    compliance_restrictions: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hcp_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("hcps.id"), nullable=True
    )
    hcp_name: Mapped[str] = mapped_column(String(255), default="")  # denormalized
    interaction_type: Mapped[str] = mapped_column(String(64), default="")
    interaction_date: Mapped[str] = mapped_column(String(32), default="")
    interaction_time: Mapped[str] = mapped_column(String(32), default="")
    topics_discussed: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(32), default="Unknown")
    outcomes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    hcp: Mapped["HCP | None"] = relationship("HCP")
    attendees: Mapped[list["InteractionAttendee"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    materials: Mapped[list["InteractionMaterial"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    samples: Mapped[list["InteractionSample"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list["FollowUpAction"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan"
    )


class InteractionAttendee(Base):
    __tablename__ = "interaction_attendees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interactions.id")
    )
    name: Mapped[str] = mapped_column(String(255))
    interaction: Mapped["Interaction"] = relationship(back_populates="attendees")


class InteractionMaterial(Base):
    __tablename__ = "interaction_materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interactions.id")
    )
    material_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    material_name: Mapped[str] = mapped_column(String(255))
    interaction: Mapped["Interaction"] = relationship(back_populates="materials")


class InteractionSample(Base):
    __tablename__ = "interaction_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interactions.id")
    )
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    batch_number: Mapped[str] = mapped_column(String(128), default="")
    interaction: Mapped["Interaction"] = relationship(back_populates="samples")


class FollowUpAction(Base):
    __tablename__ = "follow_up_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interactions.id"), nullable=True
    )
    action_text: Mapped[str] = mapped_column(Text)
    due_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="Open")
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    interaction: Mapped["Interaction"] = relationship(back_populates="follow_ups")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interactions.id"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_prompt: Mapped[str] = mapped_column(Text, default="")
    tool_called: Mapped[str] = mapped_column(String(64), default="")
    previous_state: Mapped[str] = mapped_column(Text, default="")
    new_state: Mapped[str] = mapped_column(Text, default="")
    model_used: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ApprovedMaterial(Base):
    __tablename__ = "approved_materials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    category: Mapped[str] = mapped_column(String(128), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("name", name="uq_approved_material_name"),)
