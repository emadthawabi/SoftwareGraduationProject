"""العملاء

Tables in this file:
    clients  العملاء
"""
import enum

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, StandardMixin, text_enum


class ClientType(str, enum.Enum):
    individual = "individual"  # فرد
    company = "company"        # شركة


class Client(StandardMixin, Base):
    """العملاء"""
    __tablename__ = "clients"  # العملاء

    type: Mapped[ClientType] = mapped_column(text_enum(ClientType, 20))  # النوع (فرد / شركة)
    name: Mapped[str] = mapped_column(String(200))                       # الاسم
    national_id: Mapped[str | None] = mapped_column(String(50))          # رقم الهوية / رقم التسجيل
    phone: Mapped[str | None] = mapped_column(String(50))                # الهاتف
    email: Mapped[str | None] = mapped_column(String(200))               # البريد الإلكتروني
    address: Mapped[str | None] = mapped_column(String(300))             # العنوان
    notes: Mapped[str | None] = mapped_column(Text)                      # ملاحظات

    __table_args__ = (Index("ix_clients_office_name", "office_id", "name"),)
