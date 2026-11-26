"""القضايا التنفيذية: enforcement files and their children.

Tables in this file:
    execs               الملفات التنفيذية
    exec_debtors        مدينو الملف التنفيذي
    exec_pay            دفعات التنفيذ
    exec_disbursements  تسليم مبالغ التنفيذ
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, ForeignKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CurrencyMixin, Money, StandardMixin, text_enum
from app.models.finance import PaymentMethod
from app.models.matter import MatterType


class Exec(StandardMixin, Base):
    """الملفات التنفيذية: detail of a matter of type enforcement. Shares the matter's id."""
    __tablename__ = "execs"  # الملفات التنفيذية

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)                             # = معرّف الملف القانوني
    matter_type: Mapped[MatterType] = mapped_column(
        text_enum(MatterType, 20), default=MatterType.enforcement,
        server_default=MatterType.enforcement.value,
    )                                                                                   # نوع الملف (دائمًا تنفيذ)
    exec_no: Mapped[str | None] = mapped_column(String(50))                             # رقم الملف التنفيذي
    # OPEN: free text for now; may become a fixed list like the courts.
    department: Mapped[str | None] = mapped_column(String(200))                         # دائرة التنفيذ
    bond: Mapped[str | None] = mapped_column(Text)                                      # سند التنفيذ
    original_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"))  # القضية الأصلية
    value: Mapped[Decimal | None] = mapped_column(Money())                              # قيمة التنفيذ (₪)
    # Computed, not stored: المحصّل (collected), المتبقي (remaining), غير المسلّم (not handed over).

    __table_args__ = (
        ForeignKeyConstraint(["id", "matter_type"], ["matters.id", "matters.type"]),
        CheckConstraint("matter_type = 'enforcement'", name="matter_type_is_enforcement"),
    )


class ExecDebtor(StandardMixin, Base):
    """مدينو الملف التنفيذي: more than one per file is allowed."""
    __tablename__ = "exec_debtors"  # مدينو الملف التنفيذي

    exec_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execs.id"), index=True)  # الملف التنفيذي
    name: Mapped[str] = mapped_column(String(200))                                  # الاسم
    address: Mapped[str | None] = mapped_column(String(300))                        # العنوان
    notes: Mapped[str | None] = mapped_column(Text)                                 # ملاحظات


class ExecPayment(StandardMixin, CurrencyMixin, Base):
    """دفعات التنفيذ: money collected from the debtor."""
    __tablename__ = "exec_pay"  # دفعات التنفيذ

    exec_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execs.id"), index=True)              # الملف التنفيذي
    amount: Mapped[Decimal] = mapped_column(Money())                                            # المبلغ (₪)
    paid_on: Mapped[date] = mapped_column(Date)                                                 # التاريخ
    receipt_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))  # سند القبض (مرفق)
    notes: Mapped[str | None] = mapped_column(Text)                                             # ملاحظات


class ExecDisbursement(StandardMixin, CurrencyMixin, Base):
    """تسليم مبالغ التنفيذ: handing collected money to the client, in instalments."""
    __tablename__ = "exec_disbursements"  # تسليم مبالغ التنفيذ

    exec_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execs.id"), index=True)              # الملف التنفيذي
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)          # المستفيد (موكل)
    amount: Mapped[Decimal] = mapped_column(Money())                                            # المبلغ (₪)
    handed_on: Mapped[date] = mapped_column(Date)                                               # تاريخ التسليم
    method: Mapped[PaymentMethod | None] = mapped_column(text_enum(PaymentMethod, 20))          # طريقة التسليم
    receipt_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))  # سند التسليم (مرفق)
    handled_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))             # الموظف المسؤول
    notes: Mapped[str | None] = mapped_column(Text)                                             # ملاحظات
