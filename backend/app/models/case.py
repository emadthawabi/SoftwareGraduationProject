"""القضايا: cases and their children (opponents, stages, hearings, judgments, deadlines).

Tables in this file:
    cases      القضايا
    case_opps  خصوم القضية
    stages     مراحل القضية
    sessions   الجلسات
    judgments  الأحكام والقرارات
    deadlines  المواعيد القانونية
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Money, StandardMixin, text_enum
from app.models.matter import MatterType


class CaseType(str, enum.Enum):
    # OPEN: taken from the frontend demo. The real list comes from the lawyer.
    personal_status = "personal_status"  # أحوال شخصية
    real_estate = "real_estate"          # عقاري
    labour = "labour"                    # عمالي
    commercial = "commercial"            # تجاري


class FeesPayer(str, enum.Enum):
    office = "office"  # المكتب
    client = "client"  # الموكل


class StageLevel(str, enum.Enum):
    # OPEN: other stages beyond these three are an open question.
    first_instance = "first_instance"  # ابتدائي
    appeal = "appeal"                  # استئناف
    cassation = "cassation"            # نقض


class Court(str, enum.Enum):
    # OPEN: taken from the frontend demo. The real list comes from the lawyer.
    nablus_first_instance = "nablus_first_instance"  # محكمة بداية نابلس
    court_of_appeal = "court_of_appeal"              # محكمة الاستئناف
    labour_court = "labour_court"                    # محكمة العمل
    nablus_commercial = "nablus_commercial"          # محكمة نابلس التجارية


class StageStatus(str, enum.Enum):
    # OPEN: the design names a status but not its values.
    ongoing = "ongoing"  # جارية
    ended = "ended"      # منتهية


class SessionStatus(str, enum.Enum):
    scheduled = "scheduled"  # مجدولة
    held = "held"            # عقدت
    postponed = "postponed"  # مؤجلة
    cancelled = "cancelled"  # ملغاة


class JudgmentKind(str, enum.Enum):
    # OPEN: values not given in the design; from the table name الأحكام والقرارات.
    judgment = "judgment"  # حكم
    decision = "decision"  # قرار


class DeadlineKind(str, enum.Enum):
    challenge = "challenge"  # طعن
    appeal = "appeal"        # استئناف
    cassation = "cassation"  # نقض
    other = "other"          # غيره


class DeadlineStatus(str, enum.Enum):
    # OPEN: values not given. "The system calculates, a lawyer verifies."
    calculated = "calculated"  # محسوب (بانتظار التحقق)
    verified = "verified"      # معتمد
    closed = "closed"          # منتهٍ


class Case(StandardMixin, Base):
    """القضايا: detail of a matter of type case. Shares the matter's id."""
    __tablename__ = "cases"  # القضايا

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)                      # = معرّف الملف القانوني
    matter_type: Mapped[MatterType] = mapped_column(
        text_enum(MatterType, 20), default=MatterType.case, server_default=MatterType.case.value
    )                                                                            # نوع الملف (دائمًا قضية)
    case_type: Mapped[CaseType | None] = mapped_column(text_enum(CaseType, 40))  # نوع القضية
    filed_on: Mapped[date | None] = mapped_column(Date)                          # تاريخ رفع الدعوى
    claim_value: Mapped[Decimal | None] = mapped_column(Money())                 # قيمة الدعوى (₪)
    estimated_fees: Mapped[Decimal | None] = mapped_column(Money())              # الرسوم المقدرة (₪)
    fees_payer: Mapped[FeesPayer | None] = mapped_column(text_enum(FeesPayer, 20))  # دافع الرسوم (المكتب / الموكل)
    # Computed in queries, not stored: المرحلة الحالية (current stage), الجلسة القادمة (next session).

    __table_args__ = (
        ForeignKeyConstraint(["id", "matter_type"], ["matters.id", "matters.type"]),
        CheckConstraint("matter_type = 'case'", name="matter_type_is_case"),
    )


class CaseOpponent(StandardMixin, Base):
    """خصوم القضية: more than one per case is allowed."""
    __tablename__ = "case_opps"  # خصوم القضية

    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)  # القضية
    name: Mapped[str] = mapped_column(String(200))                                  # الاسم
    address: Mapped[str | None] = mapped_column(String(300))                        # العنوان
    notes: Mapped[str | None] = mapped_column(Text)                                 # ملاحظات


class Stage(StandardMixin, Base):
    """مراحل القضية"""
    __tablename__ = "stages"  # مراحل القضية

    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)         # القضية
    previous_stage_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("stages.id"))   # المرحلة السابقة
    level: Mapped[StageLevel] = mapped_column(text_enum(StageLevel))                       # المرحلة
    court: Mapped[Court | None] = mapped_column(text_enum(Court, 50))                      # المحكمة
    case_no: Mapped[str | None] = mapped_column(String(50))                                # رقم الدعوى في هذه المرحلة
    started_on: Mapped[date | None] = mapped_column(Date)                                  # تاريخ البدء
    ended_on: Mapped[date | None] = mapped_column(Date)                                    # تاريخ الانتهاء
    status: Mapped[StageStatus] = mapped_column(
        text_enum(StageStatus, 20), default=StageStatus.ongoing, server_default=StageStatus.ongoing.value
    )                                                                                      # الحالة


class CourtSession(StandardMixin, Base):
    """الجلسات (court hearings). Named CourtSession to avoid confusion with database sessions."""
    __tablename__ = "sessions"  # الجلسات

    stage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stages.id"), index=True)          # المرحلة
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))                    # الموعد (التاريخ والوقت)
    status: Mapped[SessionStatus] = mapped_column(
        text_enum(SessionStatus, 20), default=SessionStatus.scheduled,
        server_default=SessionStatus.scheduled.value,
    )                                                                                          # الحالة
    attending_lawyer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))      # المحامي الحاضر
    # Set when the attending lawyer attends on behalf of another lawyer (إنابة).
    substituting_for_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))      # بإنابة عن (المحامي المنيب)
    previous_session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"))   # الجلسة السابقة (إعادة جدولة)
    minutes_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))  # محضر الجلسة (مرفق)
    notes: Mapped[str | None] = mapped_column(Text)                                            # ملاحظات
    postponement_reason: Mapped[str | None] = mapped_column(Text)                              # سبب التأجيل
    decision: Mapped[str | None] = mapped_column(Text)                                         # قرار الجلسة


class Judgment(StandardMixin, Base):
    """الأحكام والقرارات"""
    __tablename__ = "judgments"  # الأحكام والقرارات

    stage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stages.id"), index=True)         # المرحلة
    kind: Mapped[JudgmentKind] = mapped_column(text_enum(JudgmentKind, 20))                  # نوع القرار
    issued_on: Mapped[date] = mapped_column(Date)                                            # تاريخ الصدور
    result: Mapped[str | None] = mapped_column(Text)                                         # النتيجة
    notified_on: Mapped[date | None] = mapped_column(Date)                                   # تاريخ التبليغ (إن وجد)
    copy_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("s_attach.id"))  # نسخة الحكم (مرفق)


class Deadline(StandardMixin, Base):
    """المواعيد القانونية: the system calculates, a lawyer verifies."""
    __tablename__ = "deadlines"  # المواعيد القانونية

    matter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("matters.id"), index=True)       # الملف القانوني
    judgment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("judgments.id"))        # الحكم
    kind: Mapped[DeadlineKind] = mapped_column(text_enum(DeadlineKind, 20))                  # نوع الموعد
    affected_party: Mapped[str | None] = mapped_column(String(200))                          # الطرف المعني
    trigger_event: Mapped[str | None] = mapped_column(String(300))                           # الحدث المنشئ
    starts_on: Mapped[date | None] = mapped_column(Date)                                     # تاريخ بدء الحساب
    # OPEN: the appeal period and its starting event are open questions.
    duration_days: Mapped[int | None] = mapped_column(Integer)                               # المدة (أيام)
    legal_basis: Mapped[str | None] = mapped_column(Text)                                    # الأساس القانوني
    calculated_on: Mapped[date | None] = mapped_column(Date)                                 # الموعد المحسوب
    approved_on: Mapped[date | None] = mapped_column(Date)                                   # الموعد المعتمد
    change_reason: Mapped[str | None] = mapped_column(Text)                                  # سبب التعديل
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))         # المحامي المتحقق
    status: Mapped[DeadlineStatus] = mapped_column(
        text_enum(DeadlineStatus, 20), default=DeadlineStatus.calculated,
        server_default=DeadlineStatus.calculated.value,
    )                                                                                        # الحالة
