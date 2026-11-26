"""سجل التعديلات: append-only. No StandardMixin (rows are never updated or deleted).

Tables in this file:
    audit  سجل التعديلات
"""
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JsonB, text_enum


class AuditAction(str, enum.Enum):
    create = "create"                # إضافة
    update = "update"                # تعديل
    delete = "delete"                # حذف
    archive = "archive"              # أرشفة
    login_success = "login_success"  # دخول ناجح
    login_failure = "login_failure"  # دخول فاشل


class AuditLog(Base):
    """سجل التعديلات"""
    __tablename__ = "audit"  # سجل التعديلات

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)          # المعرّف
    office_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offices.id"), index=True)   # المكتب
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))            # المستخدم (فارغ لأحداث النظام)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # الوقت
    table_name: Mapped[str] = mapped_column(String(63))                                  # اسم الجدول
    record_id: Mapped[uuid.UUID] = mapped_column()                                       # معرّف السجل
    action: Mapped[AuditAction] = mapped_column(text_enum(AuditAction))                  # الإجراء
    before: Mapped[dict[str, Any] | None] = mapped_column(JsonB)                         # القيم السابقة
    after: Mapped[dict[str, Any] | None] = mapped_column(JsonB)                          # القيم اللاحقة

    __table_args__ = (Index("ix_audit_record", "office_id", "table_name", "record_id"),)
