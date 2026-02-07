from django.test import TestCase
from django.utils import timezone

from users.models import User
from tasks.models import TeamList, Task


class TaskModelStatusSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.project = TeamList.objects.create(name='P1', created_by=self.user)

    def test_mark_done_sets_completed_flags(self):
        task = Task.objects.create(
            title='T1',
            list=self.project,
            assigned_to=self.user,
            created_by=self.user,
        )
        task.status = Task.Status.DONE
        task.save(update_fields=['status'])
        task.refresh_from_db()

        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)

    def test_unset_done_clears_completed_flags(self):
        task = Task.objects.create(
            title='T1',
            list=self.project,
            assigned_to=self.user,
            created_by=self.user,
            status=Task.Status.DONE,
        )
        task.save()
        task.refresh_from_db()
        self.assertTrue(task.is_completed)
        self.assertIsNotNone(task.completed_at)

        task.status = Task.Status.NEW
        task.save(update_fields=['status'])
        task.refresh_from_db()

        self.assertFalse(task.is_completed)
        self.assertIsNone(task.completed_at)

    def test_in_progress_sets_started_at(self):
        task = Task.objects.create(
            title='T1',
            list=self.project,
            assigned_to=self.user,
            created_by=self.user,
        )
        self.assertIsNone(task.started_at)

        task.status = Task.Status.IN_PROGRESS
        task.save(update_fields=['status'])
        task.refresh_from_db()

        self.assertIsNotNone(task.started_at)
