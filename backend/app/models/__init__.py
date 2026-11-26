"""Importing this package registers every table on Base.metadata (needed by Alembic)."""
from app.models.audit import AuditAction, AuditLog  # noqa: F401
from app.models.case import (  # noqa: F401
    Case, CaseOpponent, CaseType, Court, CourtSession, Deadline, DeadlineKind, DeadlineStatus,
    FeesPayer, Judgment, JudgmentKind, SessionStatus, Stage, StageLevel, StageStatus,
)
from app.models.client import Client, ClientType  # noqa: F401
from app.models.execution import Exec, ExecDebtor, ExecDisbursement, ExecPayment  # noqa: F401
from app.models.finance import (  # noqa: F401
    FeeInstallment, Invoice, InvoiceLine, InvoiceLineKind, InvoiceStatus, PaymentAllocation,
    PaymentMethod, Receipt, ReceiptEntryStatus,
)
from app.models.lists import ListItem, ListKind  # noqa: F401
from app.models.matter import Matter, MatterStatus, MatterType  # noqa: F401
from app.models.office import AuthSession, Office, OfficeStatus, User, UserRole  # noqa: F401
from app.models.office_file import (  # noqa: F401
    CompanyDetails, CompanyLegalStatus, LandDetails, OfficeFile, OfficeFileKind,
)
from app.models.shared import (  # noqa: F401
    Attachment, Expense, ExpenseKind, LawyerRole, MatterClient, MatterLawyer, Procedure,
    RequiredItem, RequiredItemStatus, Task, TaskKind, TaskStatus,
)
