"""الجداول المشتركة: children shared by every kind of matter. All point at matters.

Tables in this file:
    s_clients  الموكلون
    s_lawyers  المحامون
    s_proc     الإجراءات
    s_req      البنود المطلوبة
    s_tasks    المهام (خطة العمل)
    s_exp      المصاريف والرسوم
    s_attach   المرفقات

"Who recorded / uploaded it and when" (من سجله، الرافع، تاريخ الرفع) is the standard
created_by / created_at, so it is not repeated here.
"""
import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, ForeignKey, Index, String, Text, UniqueConstraint,
)
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CurrencyMixin, Money, StandardMixin, text_enum


class LawyerRole(str, enum.Enum):
    principal = "principal"  # رئيسي
    assistant = "assistant"  # مساعد


class RequiredItemStatus(str, enum.Enum):
    pending = "pending"    # لم يتم
    received = "received"  # تم الاستلام


class TaskKind(str, enum.Enum):
    work = "work"                              # عمل
    request = "request"                        # طلب
    upcoming_procedure = "upcoming_procedure"  # إجراء قادم


class TaskStatus(str, enum.Enum):
    pending = "pending"  # لم يتم
    done = "done"        # تم


class ExpenseKind(str, enum.Enum):
    expense = "expense"    # مصروف
    paid_fee = "paid_fee"  # رسم مدفوع


class MatterClient(StandardMixin, Base):
    """الموكلون: a matter can have more than one client; at most one is principal."""
    __tablename__ = "s_clients"  # الموكلون

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)  # العميل
    is_principal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")  # موكل رئيسي

    __table_args__ = (
        UniqueConstraint("matter_id", "client_id"),
        Index(
            "uq_s_clients_one_principal", "matter_id", unique=True,
            postgresql_where=sql_text("is_principal AND deleted_at IS NULL"),
            sqlite_where=sql_text("is_principal AND deleted_at IS NULL"),
        ),
    )


class MatterLawyer(StandardMixin, Base):
    """المحامون: lawyers on the matter."""
    __tablename__ = "s_lawyers"  # المحامون

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)      # المحامي
    role: Mapped[LawyerRole] = mapped_column(text_enum(LawyerRole, 20))                 # الدور (رئيسي / مساعد)

    __table_args__ = (UniqueConstraint("matter_id", "user_id"),)


class Procedure(StandardMixin, Base):
    """الإجراءات: procedures already done."""
    __tablename__ = "s_proc"  # الإجراءات

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني
    stage_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stages.id"))         # المرحلة (للقضايا فقط)
    done_on: Mapped[date] = mapped_column(Date)                                         # تاريخ الإجراء
    text: Mapped[str] = mapped_column(Text)                                             # النص


class RequiredItem(StandardMixin, Base):
    """البنود المطلوبة: evidence or papers still needed."""
    __tablename__ = "s_req"  # البنود المطلوبة

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)     # الملف القانوني
    text: Mapped[str] = mapped_column(Text)                                                # النص (بينة أو ورقة مطلوبة)
    due_on: Mapped[date | None] = mapped_column(Date)                                      # آخر موعد
    status: Mapped[RequiredItemStatus] = mapped_column(
        text_enum(RequiredItemStatus, 20), default=RequiredItemStatus.pending,
        server_default=RequiredItemStatus.pending.value,
    )                                                                                      # الحالة
    received_on: Mapped[date | None] = mapped_column(Date)                                 # تاريخ الاستلام
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))     # المرفق


class Task(StandardMixin, Base):
    """المهام (خطة العمل)"""
    __tablename__ = "s_tasks"  # المهام (خطة العمل)

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)     # الملف القانوني
    text: Mapped[str] = mapped_column(Text)                                                # النص
    kind: Mapped[TaskKind] = mapped_column(
        text_enum(TaskKind, 30), default=TaskKind.work, server_default=TaskKind.work.value
    )                                                                                      # نوع المهمة
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)  # المسؤول
    due_on: Mapped[date | None] = mapped_column(Date)                                      # الموعد
    status: Mapped[TaskStatus] = mapped_column(
        text_enum(TaskStatus, 20), default=TaskStatus.pending, server_default=TaskStatus.pending.value
    )                                                                                      # الحالة
    done_on: Mapped[date | None] = mapped_column(Date)                                     # تاريخ الإنجاز
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))     # المرفق (الملف المنجز)


class Expense(StandardMixin, CurrencyMixin, Base):
    """المصاريف والرسوم: an empty matter_id means a general office expense."""
    __tablename__ = "s_exp"  # المصاريف والرسوم

    matter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني (فارغ = مصروف عام)
    kind: Mapped[ExpenseKind] = mapped_column(text_enum(ExpenseKind, 20))                     # النوع (مصروف / رسم مدفوع)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lists.id"))             # التصنيف (من القوائم)
    description: Mapped[str] = mapped_column(String(300))                                     # البيان
    amount: Mapped[Decimal] = mapped_column(Money())                                          # المبلغ (₪)
    spent_on: Mapped[date] = mapped_column(Date)                                              # التاريخ
    voucher_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))  # سند الصرف (مرفق)


class Attachment(StandardMixin, Base):
    """المرفقات: the file is on disk; only a pointer is stored here.

    Owner: one matter, OR one client, OR neither (a general office document).
    """
    __tablename__ = "s_attach"  # المرفقات

    matter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matters.id"), index=True)  # الملف القانوني
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)  # العميل
    name: Mapped[str] = mapped_column(String(255))                                            # الاسم
    mime_type: Mapped[str] = mapped_column(String(127))                                       # نوع الملف (MIME)
    size_bytes: Mapped[int] = mapped_column(BigInteger)                                       # الحجم (بايت)
    storage_key: Mapped[str] = mapped_column(String(500))                                     # مفتاح التخزين (مكان الحفظ)
    sha256: Mapped[str] = mapped_column(String(64))                                           # بصمة SHA-256
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lists.id"))             # التصنيف (من القوائم)

    __table_args__ = (
        CheckConstraint("matter_id IS NULL OR client_id IS NULL", name="one_owner"),
    )
