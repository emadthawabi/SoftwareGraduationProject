"""المكاتب، المستخدمون، جلسات الدخول

Tables in this file:
    offices        المكاتب
    users          المستخدمون
    auth_sessions  جلسات الدخول
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, StandardMixin, text_enum


class OfficeStatus(str, enum.Enum):
    active = "active"        # فعّال
    suspended = "suspended"  # موقوف


class UserRole(str, enum.Enum):
    # Stored only. Not enforced yet (all users of an office are equal for now).
    admin = "admin"          # أدمن
    lawyer = "lawyer"        # محامي
    secretary = "secretary"  # سكرتير


class Office(Base):
    """المكاتب

    No StandardMixin: an office cannot belong to an office. Never deleted, only suspended.
    """
    __tablename__ = "offices"  # المكاتب

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)  # المعرّف
    name: Mapped[str] = mapped_column(String(200))                                # الاسم
    phone: Mapped[str | None] = mapped_column(String(50))                         # الهاتف
    address: Mapped[str | None] = mapped_column(String(300))                      # العنوان
    status: Mapped[OfficeStatus] = mapped_column(
        text_enum(OfficeStatus), default=OfficeStatus.active, server_default=OfficeStatus.active.value
    )                                                                             # الحالة (فعّال / موقوف)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # تاريخ الإنشاء
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )                                                                             # تاريخ آخر تعديل


class User(StandardMixin, Base):
    """المستخدمون

    Users are only deactivated (is_active = false), never deleted: deleted_at stays empty.
    """
    __tablename__ = "users"  # المستخدمون

    name: Mapped[str] = mapped_column(String(200))                                # الاسم
    # OPEN: unique across the whole database (exception to rule 5), because the office
    # is not known at login. Needs approval.
    email: Mapped[str] = mapped_column(String(254), unique=True)                  # البريد الإلكتروني (للدخول)
    password_hash: Mapped[str] = mapped_column(String(255))                       # تجزئة كلمة المرور Argon2id
    phone: Mapped[str | None] = mapped_column(String(50))                         # الهاتف
    role: Mapped[UserRole] = mapped_column(text_enum(UserRole))                   # الدور
    license_no: Mapped[str | None] = mapped_column(String(50))                    # رقم رخصة المحاماة
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")  # فعّال / موقوف
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )                                                                             # يجب تغيير كلمة المرور
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # عدد محاولات الدخول الفاشلة
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # مقفل حتى
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # آخر دخول


class AuthSession(Base):
    """جلسات الدخول (refresh tokens). Not court sessions: those are CourtSession.

    No StandardMixin: rows are revoked, never edited or soft-deleted.
    """
    __tablename__ = "auth_sessions"  # جلسات الدخول

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)  # المعرّف
    office_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offices.id"), index=True)  # المكتب
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)      # المستخدم
    refresh_token_hash: Mapped[str] = mapped_column(String(64), index=True)       # تجزئة رمز التحديث (SHA-256)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # تاريخ الإنشاء
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))         # تاريخ الانتهاء
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # تاريخ الإلغاء
    user_agent: Mapped[str | None] = mapped_column(String(500))                   # المتصفح / الجهاز
    ip_address: Mapped[str | None] = mapped_column(String(45))                    # عنوان IP
