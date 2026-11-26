"""ملفات المكتب: office files (general / company / land) and their two detail tables.

Tables in this file:
    ofiles        ملفات المكتب
    comp_details  تفاصيل ملف الشركة
    land_details  تفاصيل ملف الأرض

Same pattern as matters: comp_details and land_details share the office file's id and
repeat its kind, with a composite foreign key (id, kind) -> ofiles(id, kind).
"""
import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, ForeignKeyConstraint, Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, StandardMixin, text_enum
from app.models.matter import MatterType


class OfficeFileKind(str, enum.Enum):
    general = "general"  # عام
    company = "company"  # شركة
    land = "land"        # أرض


class CompanyLegalStatus(str, enum.Enum):
    being_formed = "being_formed"      # قيد التأسيس
    registered = "registered"          # مسجلة
    in_liquidation = "in_liquidation"  # قيد التصفية


class OfficeFile(StandardMixin, Base):
    """ملفات المكتب: detail of a matter of type office. Shares the matter's id."""
    __tablename__ = "ofiles"  # ملفات المكتب

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)                       # = معرّف الملف القانوني
    matter_type: Mapped[MatterType] = mapped_column(
        text_enum(MatterType, 20), default=MatterType.office, server_default=MatterType.office.value
    )                                                                             # نوع الملف (دائمًا مكتب)
    kind: Mapped[OfficeFileKind] = mapped_column(text_enum(OfficeFileKind, 20))   # النوع (عام / شركة / أرض)
    # OPEN: free text for now (consultation, contract, legal warning...); may become a fixed list.
    classification: Mapped[str | None] = mapped_column(String(100))               # تصنيف الملف
    # Computed, not stored: الرسوم المدفوعة (from s_exp), الإجراء القادم (from s_tasks).

    __table_args__ = (
        ForeignKeyConstraint(["id", "matter_type"], ["matters.id", "matters.type"]),
        CheckConstraint("matter_type = 'office'", name="matter_type_is_office"),
        UniqueConstraint("id", "kind"),  # target of the detail tables' composite foreign key
    )


class CompanyDetails(StandardMixin, Base):
    """تفاصيل ملف الشركة: one per office file of kind company."""
    __tablename__ = "comp_details"  # تفاصيل ملف الشركة

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)                     # = معرّف ملف المكتب
    kind: Mapped[OfficeFileKind] = mapped_column(
        text_enum(OfficeFileKind, 20), default=OfficeFileKind.company,
        server_default=OfficeFileKind.company.value,
    )                                                                           # نوع ملف المكتب (دائمًا شركة)
    company_name: Mapped[str] = mapped_column(String(200))                      # اسم الشركة
    registration_no: Mapped[str | None] = mapped_column(String(50))             # رقم التسجيل
    company_type: Mapped[str | None] = mapped_column(String(100))               # نوع الشركة
    registered_on: Mapped[date | None] = mapped_column(Date)                    # تاريخ التسجيل
    registrar: Mapped[str | None] = mapped_column(String(200))                  # الجهة المتابعة (مراقب الشركات)
    legal_status: Mapped[CompanyLegalStatus | None] = mapped_column(
        text_enum(CompanyLegalStatus, 20)
    )                                                                           # الحالة القانونية

    __table_args__ = (
        ForeignKeyConstraint(["id", "kind"], ["ofiles.id", "ofiles.kind"]),
        CheckConstraint("kind = 'company'", name="kind_is_company"),
    )


class LandDetails(StandardMixin, Base):
    """تفاصيل ملف الأرض: one per office file of kind land."""
    __tablename__ = "land_details"  # تفاصيل ملف الأرض

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)                     # = معرّف ملف المكتب
    kind: Mapped[OfficeFileKind] = mapped_column(
        text_enum(OfficeFileKind, 20), default=OfficeFileKind.land, server_default=OfficeFileKind.land.value
    )                                                                           # نوع ملف المكتب (دائمًا أرض)
    parcel_no: Mapped[str | None] = mapped_column(String(50))                   # رقم القطعة
    basin_no: Mapped[str | None] = mapped_column(String(50))                    # رقم الحوض
    area_name: Mapped[str | None] = mapped_column(String(200))                  # المنطقة / القرية
    # OPEN: unit not given (m² or dunum).
    size: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))                # المساحة
    # OPEN: free text for now (registration, partition, ownership transfer...).
    procedure_type: Mapped[str | None] = mapped_column(String(100))             # نوع الإجراء
    registry_office: Mapped[str | None] = mapped_column(String(200))            # دائرة الطابو المختصة

    __table_args__ = (
        ForeignKeyConstraint(["id", "kind"], ["ofiles.id", "ofiles.kind"]),
        CheckConstraint("kind = 'land'", name="kind_is_land"),
    )
