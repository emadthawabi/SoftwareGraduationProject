"""الملفات القانونية: the parent of every file (case, enforcement, office file).

Tables in this file:
    matters  الملفات القانونية

Each matter has exactly one detail row matching its type, in cases / execs / ofiles.
The detail tables share the matter's id and repeat its type. A composite foreign key
(id, type) -> matters(id, type) makes a wrong type impossible in the database.
"Exactly one" (a matter must not stay without its detail row) is checked in code and
will get a deferred database trigger in the matters migration.
"""
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CurrencyMixin, Money, StandardMixin, text_enum


class MatterType(str, enum.Enum):
    case = "case"                # قضية
    enforcement = "enforcement"  # ملف تنفيذي
    office = "office"            # ملف مكتب


class MatterStatus(str, enum.Enum):
    # OPEN: the three kinds use different words. This maps them to one shared set;
    # office files use only open / closed. Needs confirmation.
    open = "open"        # جارية (قضية) / جارٍ (تنفيذ) / مفتوح (مكتب)
    on_hold = "on_hold"  # معلقة / معلق
    closed = "closed"    # مغلقة / منتهٍ / مغلق


class Matter(StandardMixin, CurrencyMixin, Base):
    """الملفات القانونية"""
    __tablename__ = "matters"  # الملفات القانونية

    type: Mapped[MatterType] = mapped_column(text_enum(MatterType, 20))         # نوع الملف (قضية / تنفيذ / مكتب)
    title: Mapped[str] = mapped_column(String(300))                             # العنوان
    # OPEN: numbering format is an open question; stored as text.
    internal_no: Mapped[str] = mapped_column(String(50))                        # الرقم الداخلي (فريد داخل المكتب)
    status: Mapped[MatterStatus] = mapped_column(
        text_enum(MatterStatus, 20), default=MatterStatus.open, server_default=MatterStatus.open.value
    )                                                                           # الحالة
    opened_on: Mapped[date | None] = mapped_column(Date)                        # تاريخ الفتح
    closed_on: Mapped[date | None] = mapped_column(Date)                        # تاريخ الإغلاق
    close_reason: Mapped[str | None] = mapped_column(Text)                      # سبب الإغلاق
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # تاريخ الأرشفة (ليس حذفًا)
    agreed_fee: Mapped[Decimal | None] = mapped_column(Money())                 # الأتعاب المتفق عليها (₪)
    notes: Mapped[str | None] = mapped_column(Text)                             # ملاحظات

    __table_args__ = (
        UniqueConstraint("office_id", "internal_no"),
        UniqueConstraint("id", "type"),  # target of the detail tables' composite foreign key
    )
