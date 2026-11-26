import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, MetaData, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Fixed constraint names, so Alembic migrations can always find and drop them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ---------------------------------------------------------------------------
# Shared column types
# ---------------------------------------------------------------------------

def Money():
    """Exact amount in ₪. Never a float."""
    return Numeric(14, 2)


def text_enum(enum_cls: type[enum.Enum], length: int = 30) -> Enum:
    """A fixed list stored as plain text: adding a value needs no migration."""
    return Enum(enum_cls, native_enum=False, length=length)


# JSONB on PostgreSQL, plain JSON on SQLite (used by the tests).
JsonB = JSON().with_variant(JSONB(), "postgresql")


class CurrencyMixin:
    """العملة: kept by design, always ILS (₪). Never used for logic."""

    currency: Mapped[str] = mapped_column(String(3), default="ILS", server_default="ILS")  # العملة


# ---------------------------------------------------------------------------
# Standard columns
# ---------------------------------------------------------------------------

class StandardMixin:
    """The standard fields every table carries."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)  # المعرّف
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # تاريخ الإنشاء
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )  # تاريخ آخر تعديل
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # تاريخ الحذف (حذف منطقي)

    # Columns with a ForeignKey on a mixin must be declared with declared_attr.
    @declared_attr
    def office_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(ForeignKey("offices.id"), index=True)  # المكتب

    @declared_attr
    def created_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(ForeignKey("users.id"))  # أنشأه

    @declared_attr
    def updated_by(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(ForeignKey("users.id"))  # عدّله
