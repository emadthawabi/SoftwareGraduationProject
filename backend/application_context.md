# Project context: Law-office management system (نظام إدارة مكتب محاماة)

Read this file fully before writing any code. It is the agreed design. If something you are asked to do conflicts with it, stop and ask instead of guessing.

## 1. What this project is

A web application for a law office in Palestine/Israel. The interface is Arabic (RTL). The system manages القضايا (court cases), الملفات التنفيذية (enforcement files), ملفات المكتب (office files such as company registration and land), العملاء (clients), الجلسات (court hearings), الفواتير (invoices), المقبوضات (client payments) and المصاريف (expenses).

- The **frontend is finished** (vanilla HTML/CSS/JS, grayscale, hash routing). Do not redesign it. You will connect it to the API later.
- We are now building the **backend**: database, authentication, then the API, one entity at a time.
- Discussion and code comments are in English. Anything that appears in the application (labels, messages, table meanings) uses Arabic terms.
- Currency is **₪ only**. Money is always an exact decimal (`NUMERIC(14,2)`), never a float.

## 2. Stack

PostgreSQL, FastAPI, SQLAlchemy 2.0 (typed `Mapped` / `mapped_column`), Alembic, Pydantic v2 with pydantic-settings, PyJWT, argon2-cffi, psycopg 3, pytest, httpx.

A working reference for one table (العملاء) exists in this project. **Copy its patterns exactly** for every new table:

| File | Role |
|---|---|
| `app/core/config.py` | `Settings` from environment. `jwt_secret` has no default and is required. |
| `app/core/security.py` | `AuthContext(user_id, office_id, role)` and `get_auth`, which reads the `access_token` cookie. |
| `app/db/base.py` | `Base` and `StandardMixin` (standard columns, see section 4). |
| `app/db/session.py` | `get_db(auth)` opens the session and sets `app.office_id` for row-level security. This is the only place that opens a database session. |
| `app/models/*.py` | SQLAlchemy models. |
| `app/schemas/*.py` | Pydantic: `XCreate`, `XUpdate` (all optional), `XOut` (hides `office_id`, `deleted_at`). |
| `app/api/*.py` | Routers: list (with `q`, `limit`, `offset`), create, get, patch, soft delete. |
| `migrations/` | Alembic. |
| `tests/` | pytest. |

## 3. Rules that apply to everything

1. **Every row belongs to an office** (`office_id`). There is one office today, but the code must behave as if there were several. Every query filters on `auth.office_id`. A row from another office must return 404, as if it did not exist.
2. **Identity comes from the token, never from the request.** `office_id`, `user_id` and `role` are taken from `AuthContext`. Never accept them in a request body, query string or URL.
3. **Never really delete.** Deleting sets `deleted_at`. Every read filters `deleted_at IS NULL`. Users are only deactivated.
4. **Archive is separate from delete.** Archiving a file sets its `تاريخ الأرشفة` and keeps it readable. Do not mix the two.
5. **IDs are UUIDs.** Uniqueness is always per office, for example a unique constraint on `(office_id, internal_number)`. Never make anything unique across the whole database, because we may move to one database per office later.
6. **Only `get_db` opens sessions.** No other code creates its own engine or session. This keeps the later move to a database per office easy.
7. **Fixed lists are enums in code, stored as text.** Use `Enum(X, native_enum=False, length=N)`. Adding a value must not need a migration. Fixed lists: المحاكم (courts), أنواع القضايا (case types), الحالات (statuses), الأدوار (roles), طرق الدفع (payment methods).
8. **Files live on disk, not in the database.** The database stores only a pointer (`storage_key`, name, MIME type, size, SHA-256). Each office gets its own folder. Never store file bytes in a column.
9. **Audit log.** Every create, update, delete and archive writes a row to `audit` with the before and after values as JSONB. The audit table is append-only.
10. **Migrations.** Never edit a migration that has already been applied. Add a new one. Always check that both upgrade and downgrade run.
11. **Tests.** Every new endpoint gets tests, including: 401 without a token, validation error (422), another office gets 404, soft delete keeps the row.
12. **Do not invent columns, tables or rules.** If the design does not say it, ask.

## 4. Standard columns (`StandardMixin`)

Every table gets these from the mixin: `id` (UUID), `office_id`, `created_at`, `updated_at`, `deleted_at`, `created_by`, `updated_by`. The columns with foreign keys use `declared_attr`. Do not repeat these in a model.

Exceptions: pure child or link tables may omit `office_id` only if the design says so. Ask first.

## 5. The schema (32 tables)

The full diagram is in `docs/legal_schema_31.html` (31 tables, interactive). It is the source of truth for columns. Authentication adds one table (`auth_sessions`), making 32. Table names below are the database names. Arabic names are what the user sees.

### 5.1 The central idea: الملف القانوني (`matters`)

Instead of three unrelated kinds of files, there is one parent table, `matters`, holding what all files share: type (case / enforcement / office), title, internal number (unique per office), status, open date, close date and reason, archive date, agreed fee, notes.

Three **detail tables** extend it, one row each, sharing the parent's primary key (primary key and foreign key at once):
- `cases` (القضايا)
- `execs` (الملفات التنفيذية)
- `ofiles` (ملفات المكتب), which has its own two detail tables: `comp_details` (شركة) and `land_details` (أرض).

A matter must have exactly one detail row matching its type. Enforce this in code and with a database constraint.

All shared child tables point at `matters`, not at the three detail tables. That is why client lists, lawyers, tasks, expenses and attachments work the same for all file kinds.

### 5.2 Core (المنصة والمشترك)

| Table | Arabic | Purpose and key points |
|---|---|---|
| `offices` | المكاتب | The office: name, phone, address, status (active/suspended). |
| `users` | المستخدمون | Email (login, unique), Argon2id password hash, phone, role (أدمن / محامي / سكرتير), lawyer license number, active/deactivated, last login. Plus the authentication fields in section 6. |
| `clients` | العملاء | Type (فرد / شركة), name, national ID or registration number, phone, email, address, notes. **Already built as the reference example.** |
| `lists` | القوائم | Only office-editable lists: attachment categories and expense categories. Courts and case types are enums in code, not here. |
| `matters` | الملفات القانونية | The parent, see 5.1. |
| `invoices` | الفواتير | Linked to a matter and a client. Number unique per office, issue date, due date, status (draft / issued / cancelled), total (computed), payment status (computed). |
| `inv_lines` | بنود الفاتورة | Invoice lines: description, kind (fees / court fees / expenses), amount. |
| `fee_inst` | دفعات الأتعاب | The agreed fee instalments of a matter: amount, due date. Optionally tied to one invoice line (unique when tied). Paid amount and status are **computed** from allocations. |
| `receipts` | مقبوضات الموكل | Money received from a client: amount, date, payment method (cash / cheque / transfer), reference, receipt file (optional), who received it. |
| `payment_allocations` | تخصيص المقبوضات | Splits a receipt across invoice lines or fee instalments. See the rules below. |
| `audit` | سجل التعديلات | Append-only log (see rule 9). |

**Allocation rules (important, easy to get wrong):**
- Each allocation points at exactly one target: an invoice line **or** a fee instalment, never both and never neither.
- An instalment that is already tied to an invoice line counts through that line only. Never count it twice.
- The sum of a receipt's allocations can never exceed the receipt amount.
- Paid amounts and statuses of invoices and instalments are computed from allocations. Never store them as typed-in numbers.

### 5.3 القضايا (cases)

| Table | Arabic | Purpose and key points |
|---|---|---|
| `cases` | القضايا | Detail of a matter: case type, filing date, claim value, estimated fees, who pays the fees (office/client), current stage (computed), next session (computed). |
| `case_opps` | خصوم القضية | Opponents. **More than one is allowed.** Name, address, notes. |
| `stages` | مراحل القضية | A case passes through stages: ابتدائي, استئناف, نقض (others are an open question). Court, case number in that stage, start and end dates, status, link to the previous stage. |
| `sessions` | الجلسات | Court hearings: stage, date and time (`TIMESTAMPTZ`), status (scheduled / held / postponed / cancelled), attending lawyer, **substituting-for lawyer** (إنابة), previous session (for rescheduling), minutes attachment, notes, postponement reason, session decision. |
| `judgments` | الأحكام والقرارات | Decisions in a stage: type, date, result, notification date (if any), judgment copy attachment. |
| `deadlines` | المواعيد القانونية | Appeal and other legal deadlines: type, affected party, triggering event, start date, duration, legal basis, **calculated date**, **approved date**, reason for any change, the lawyer who verified it, status. The system calculates, a lawyer verifies. |

A different lawyer may attend a hearing than the responsible lawyer, through إنابة. This is stored on `sessions`.

### 5.4 القضايا التنفيذية (enforcement)

| Table | Arabic | Purpose and key points |
|---|---|---|
| `execs` | الملفات التنفيذية | Detail of a matter: enforcement number, enforcement department (دائرة التنفيذ), enforcement bond (سند التنفيذ), optional original case, value. Collected, remaining and not-yet-handed-over amounts are **computed**. |
| `exec_debtors` | مدينو الملف التنفيذي | Debtors: name, address, notes. More than one. |
| `exec_pay` | دفعات التنفيذ | Payments collected from the debtor: amount, date, receipt attachment. |
| `exec_disbursements` | تسليم مبالغ التنفيذ | Handing collected money over to the client: client, amount, date, method, handover receipt, responsible employee. Handover is **in instalments** (على دفعات). |

### 5.5 ملفات المكتب (office files)

`ofiles` (kind: general / company / land, classification such as consultation, contract, legal warning; the next action is computed from tasks), with `comp_details` (company name, registration number, company type, registration date, registrar, legal status) and `land_details` (parcel number, basin number, area/village, size, procedure type, land registry office).

### 5.6 Shared children (الجداول المشتركة)

All point at `matters`:

| Table | Arabic | Notes |
|---|---|---|
| `s_clients` | الموكلون | A matter can have **more than one client**. One is marked principal. |
| `s_lawyers` | المحامون | Lawyers on the matter, role principal/assistant. |
| `s_proc` | الإجراءات | Procedures done: date, text, optional stage, who recorded it. |
| `s_req` | البنود المطلوبة | Required evidence or papers: text, deadline, status, received date, optional attachment. |
| `s_tasks` | المهام (خطة العمل) | Tasks: text, kind (work / request / upcoming procedure), assignee, due date, status, completion date, attachment. |
| `s_exp` | المصاريف والرسوم | Expenses and paid fees. The matter is optional: empty means a general office expense. Category from `lists`. |
| `s_attach` | المرفقات | Attachments. Belongs to one matter **or** one client **or** the office (general document). Stores name, MIME type, size, storage key, SHA-256, uploader, upload date, category. |

## 6. Authentication (design agreed)

- Short-lived **access token** plus **rotating refresh token**. The refresh token is stored **hashed**.
- Both tokens travel in secure cookies that JavaScript cannot read (`HttpOnly`, `Secure`, `SameSite`). Never use localStorage.
- User, office and role come from the token only.
- Passwords: Argon2id.
- **One office per user.**
- Users are **only deactivated**, never deleted.
- The أدمن creates users with a **temporary password** and a "must change password" flag. The user must change it on first login.
- **Lockout:** a failed-login counter and a "locked until" time on `users`.
- Login events (success and failure) are written to the audit log.
- New table `auth_sessions` (named so to avoid confusion with court `sessions`): user, hashed refresh token, created, expires, revoked, user agent, IP.
- New fields on `users`: password hash, active, must-change-password, failed-login count, locked-until, last login.

## 7. What to build now

In this order, one step at a time, each with tests, and stop after each step for review:

1. Finish the foundation: the real `Office` and `User` models (replace the stubs), and the `auth_sessions` model with its migration.
2. Authentication endpoints: login (check password, apply lockout, set cookies), refresh (rotate), logout (revoke), change password (including the forced change), and أدمن endpoints to create and deactivate users.
3. Audit writing, as a shared helper used by every endpoint.
4. Row-level security: policies on the tables, an application database user with limited rights, and `set_config('app.office_id', ...)` per request (already started in `get_db`).
5. `matters` plus `cases` (القضايا), following the العملاء pattern. Then the case children: `case_opps`, `stages`, `sessions`, `judgments`, `deadlines`.
6. The shared children (`s_*`), then enforcement, office files, and finally invoices, receipts and allocations.

Add files gradually. Build only what the current step needs.

## 8. What NOT to build for now

- Permissions and الأتعاب visibility. All lawyers are on the same level for now. Do not add role-based restrictions beyond "authenticated user of this office". Keep `role` stored, do not enforce differences.
- More than one office, office switching, signup of new offices, a platform admin.
- Two-factor login.
- Email of any kind: invitations, password reset, confirmation.
- A database per office (design for it, do not build it).
- Multi-currency. The `currency` columns exist in 8 tables (`matters`, `invoices`, `receipts`, `fee_inst`, `payment_allocations`, `exec_pay`, `exec_disbursements`, `s_exp`). Keep them with the default `ILS` and never use them for logic.
- Drafting and document templates (الصياغة والنماذج) and integration with الميزان. Both were removed.
- Changes to the frontend look, colors or styling. That is a later phase.
- Real deletion of anything.
- Anything not in this document.

## 9. Open questions (do not decide these yourself)

These go to the lawyer. If your work depends on one, ask the user.
- Several lawyers per case and who sees which الأتعاب.
- Partial handover of enforcement payments to the client.
- Appeal period in days, and whether it counts from the judgment or from its notification.
- Retention period for archived files.
- Invoice bundling, and the invoice and file numbering format.
- رقم الأساس (base number) of a case.
- Stages beyond ابتدائي / استئناف / نقض.
- Whether permissions will later differ by role.

## 10. Known issues the user chose to keep

- The العملة columns above, despite ₪ only.
- The double-counting risk in تخصيص المقبوضات (guarded by the rules in 5.2).

## 11. How to work in this project

- Before starting a step, say what you will build and which files you will create or change.
- Follow the reference pattern. Do not introduce new libraries or structure without asking.
- Run the tests and the migration upgrade and downgrade before saying a step is done.
- Keep each step small enough to review.
- Report what you did in two or three sentences, and name the next step.