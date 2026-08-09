"""Shared dependencies for focused workflow mixins; contains no use-case logic."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from typing import Iterable
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from nicegui_app.config import DEFAULT_BACKUP_DIR, DEFAULT_DATABASE_PATH, POLICY_VERSION, PREFECT_SEED_PATH
from nicegui_app.persistence.database import create_session_factory, required_database_tables
from nicegui_app.persistence.models import (
    AuditEventRecord,
    BackupObligationRecord,
    BackupRunRecord,
    Base,
    ExternalShareOutboxRecord,
    FairnessLedgerRecord,
    LeaveAdjustmentRecord,
    LeaveDeclarationRecord,
    OperationCommandRecord,
    PrefectAvailabilityRecord,
    PrefectRecord,
    RosterAssignmentRecord,
    RosterDayClosureRecord,
    RosterSlotExceptionRecord,
    RosterWeekRecord,
)
from nicegui_app.services.maintenance import MaintenanceModeError, MaintenanceStatus, maintenance_coordinator
from nicegui_app.services.operation_context import current_operation_actor
from nicegui_app.services.workflow_types import (
    ASSIST_ASSIGNMENT_MODE_CODES,
    BackupResult,
    CommittedWriteBackupError,
    DraftAssignmentUpdateResult,
    DraftCellEdit,
    DraftDayEdit,
    DraftPatchResult,
    DraftSlotStateEdit,
    DutyAllocationEntry,
    FLEXIBLE_WEEKLY,
    FairnessDiscrepancy,
    FairnessReconciliationReport,
    FairnessTrendPoint,
    HandoverBackupPackage,
    LEGACY_FIXED_WEEKDAY,
    LeaveAdjustmentResult,
    PeriodSummaryReport,
    PREFECT_PATCH_FIELDS,
    PrefectInput,
    PrefectPatch,
    PrefectPeriodContribution,
    ROLE_CODES,
    ReportRosterSource,
    RosterWeekResult,
    RosterWithdrawalResult,
    WorkflowConflictError,
    WorkflowError,
    WorkflowMaintenanceError,
    WeekScheduleOverrides,
    prefect_input_from_patch,
)
from roster_core.generator import (
    RosterGenerationError,
    generate_weekly_roster,
    legacy_assist_weekday_mapping,
    validate_assignments,
)
from roster_core.models import Assignment, Prefect, parse_prefect_role
from roster_policy import (
    DutyPost,
    PrefectRole,
    SchoolDay,
    can_assign_role,
    duty_weight,
    is_chinese_display_name,
    required_posts_for_day,
)
