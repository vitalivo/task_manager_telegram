from __future__ import annotations

from ..models import TaskAuditLog


def log_task_action(task, actor, action, details=None) -> None:
    try:
        TaskAuditLog.objects.create(
            task=task,
            actor=actor,
            action=action,
            details=details or {},
        )
    except Exception:
        # Avoid breaking main flow for audit failures
        pass
