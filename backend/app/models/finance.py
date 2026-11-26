"""الفواتير، بنود الفاتورة، دفعات الأتعاب، مقبوضات الموكل، تخصيص المقبوضات.

Tables in this file:
    invoices             الفواتير
    inv_lines            بنود الفاتورة
    fee_inst             دفعات الأتعاب
    receipts             مقبوضات الموكل
    payment_allocations  تخصيص المقبوضات

Paid amounts and payment statuses are never stored: they are computed from
payment_allocations. Rules for allocations (see application_context.md 5.2):
- exactly one target: an invoice line OR a fee instalment (enforced below);
- an instalment tied to an invoice line counts through that line only;
- the sum of a receipt's allocations never exceeds the receipt amount.
The last two need data from other rows; they are checked in code and will get
database triggers in the finance migration.
"""
import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CurrencyMixin, Money, StandardMixin, text_enum


class PaymentMethod(str, enum.Enum):
    cash = "cash"          # نقدًا
    cheque = "cheque"      # شيك
    transfer = "transfer"  # تحويل


class InvoiceStatus(str, enum.Enum):
    draft = "draft"          # مسودة
    issued = "issued"        # صادرة
    cancelled = "cancelled"  # ملغاة


class InvoiceLineKind(str, enum.Enum):
    fees = "fees"              # أتعاب
    court_fees = "court_fees"  # رسوم
    expenses = "expenses"      # مصاريف


class ReceiptEntryStatus(str, enum.Enum):
    # OPEN: "حالة القيد" values are not given. Receipts are never deleted, so a wrong
    # one is voided.
    posted = "posted"  # مقيّد
    voided = "voided"  # ملغى


class Invoice(StandardMixin, CurrencyMixin, Base):
    """الفواتير"""
    __tablename__ = "invoices"  # الفواتير

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)  # الموكل
    # OPEN: numbering format is an open question; stored as text.
    number: Mapped[str] = mapped_column(String(50))                                     # رقم الفاتورة (فريد داخل المكتب)
    issued_on: Mapped[date | None] = mapped_column(Date)                                # تاريخ الإصدار
    due_on: Mapped[date | None] = mapped_column(Date)                                   # تاريخ الاستحقاق
    status: Mapped[InvoiceStatus] = mapped_column(
        text_enum(InvoiceStatus, 20), default=InvoiceStatus.draft, server_default=InvoiceStatus.draft.value
    )                                                                                   # حالة الإصدار
    notes: Mapped[str | None] = mapped_column(Text)                                     # ملاحظات
    # Computed, not stored: الإجمالي (total), حالة السداد (payment status).

    __table_args__ = (UniqueConstraint("office_id", "number"),)


class InvoiceLine(StandardMixin, Base):
    """بنود الفاتورة"""
    __tablename__ = "inv_lines"  # بنود الفاتورة

    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)  # الفاتورة
    description: Mapped[str] = mapped_column(String(300))                                 # البيان
    kind: Mapped[InvoiceLineKind] = mapped_column(text_enum(InvoiceLineKind, 20))         # النوع
    amount: Mapped[Decimal] = mapped_column(Money())                                      # المبلغ (₪)


class FeeInstallment(StandardMixin, CurrencyMixin, Base):
    """دفعات الأتعاب"""
    __tablename__ = "fee_inst"  # دفعات الأتعاب

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني
    # Unique when set: one instalment per invoice line. Several NULLs are allowed.
    invoice_line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inv_lines.id"), unique=True
    )                                                                                   # بند فاتورة الأتعاب
    amount: Mapped[Decimal] = mapped_column(Money())                                    # المبلغ (₪)
    due_on: Mapped[date | None] = mapped_column(Date)                                   # تاريخ الاستحقاق
    # Computed, not stored: المسدّد (paid), الحالة (status).


class Receipt(StandardMixin, CurrencyMixin, Base):
    """مقبوضات الموكل"""
    __tablename__ = "receipts"  # مقبوضات الموكل

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)       # الموكل
    amount: Mapped[Decimal] = mapped_column(Money())                                         # المبلغ (₪)
    received_on: Mapped[date] = mapped_column(Date)                                          # تاريخ القبض
    method: Mapped[PaymentMethod] = mapped_column(text_enum(PaymentMethod, 20))              # طريقة الدفع
    reference: Mapped[str | None] = mapped_column(String(100))                               # رقم الشيك أو المرجع
    receipt_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))  # سند القبض (مرفق)
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))         # المستلم
    entry_status: Mapped[ReceiptEntryStatus] = mapped_column(
        text_enum(ReceiptEntryStatus, 20), default=ReceiptEntryStatus.posted,
        server_default=ReceiptEntryStatus.posted.value,
    )                                                                                        # حالة القيد


class PaymentAllocation(StandardMixin, CurrencyMixin, Base):
    """تخصيص المقبوضات"""
    __tablename__ = "payment_allocations"  # تخصيص المقبوضات

    receipt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("receipts.id"), index=True)              # المقبوض
    invoice_line_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("inv_lines.id"), index=True)  # بند الفاتورة
    fee_installment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fee_inst.id"), index=True
    )                                                                                                 # قسط الأتعاب
    amount: Mapped[Decimal] = mapped_column(Money())                                                  # المبلغ (₪)

    __table_args__ = (
        CheckConstraint(
            "(invoice_line_id IS NULL) <> (fee_installment_id IS NULL)", name="exactly_one_target"
        ),
    )
