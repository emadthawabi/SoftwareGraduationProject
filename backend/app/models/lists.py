"""القوائم: only the lists an office can edit. Courts, case types etc. are enums in code.

Tables in this file:
    lists  القوائم
"""
import enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, StandardMixin, text_enum


class ListKind(str, enum.Enum):
    attachment_category = "attachment_category"  # تصنيف مرفقات
    expense_category = "expense_category"        # نوع مصروف


class ListItem(StandardMixin, Base):
    """القوائم"""
    __tablename__ = "lists"  # القوائم

    kind: Mapped[ListKind] = mapped_column(text_enum(ListKind))  # نوع القائمة
    name: Mapped[str] = mapped_column(String(100))              # الاسم
