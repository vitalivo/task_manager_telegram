from __future__ import annotations

from ..models import ProjectMember, TeamList, Task


def is_admin_user(user) -> bool:
    if not user:
        return False
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    try:
        return user.groups.filter(name__in=['Администраторы', 'Admins', 'admin', 'admins']).exists()
    except Exception:
        return False


def user_can_access_project(user, project: TeamList) -> bool:
    if not user or not project:
        return False
    if project.created_by_id == user.id:
        return True
    return ProjectMember.objects.filter(project=project, user=user, is_active=True).exists()


def user_is_project_manager(user, project: TeamList) -> bool:
    if not user or not project:
        return False
    if project.created_by_id == user.id:
        return True
    return ProjectMember.objects.filter(
        project=project,
        user=user,
        is_active=True,
        role=ProjectMember.Role.MANAGER,
    ).exists()


def can_edit_task(user, task: Task) -> bool:
    return (
        task.assigned_to_id == user.id
        or task.created_by_id == user.id
        or user_is_project_manager(user, task.list)
        or is_admin_user(user)
    )
