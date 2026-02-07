from django.test import TestCase

from users.models import User
from tasks.models import TeamList, Task


class TaskCompletionWebActionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')
        self.other = User.objects.create_user(username='u2', password='pass12345')
        self.project = TeamList.objects.create(name='P1', created_by=self.user)
        self.task = Task.objects.create(
            title='T1',
            list=self.project,
            assigned_to=self.user,
            created_by=self.user,
        )

    def test_uncomplete_requires_login(self):
        r = self.client.post(f'/api/v1/tasks/{self.task.id}/uncomplete/')
        self.assertEqual(r.status_code, 403)

    def test_uncomplete_by_assignee(self):
        self.task.is_completed = True
        self.task.save(update_fields=['is_completed'])
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertEqual(self.task.status, Task.Status.DONE)

        self.client.login(username='u1', password='pass12345')
        r = self.client.post(f'/api/v1/tasks/{self.task.id}/uncomplete/')
        self.assertEqual(r.status_code, 200)

        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)
        self.assertEqual(self.task.status, Task.Status.NEW)
        self.assertIsNone(self.task.completed_at)

    def test_uncomplete_forbidden_for_unrelated_user(self):
        self.client.login(username='u2', password='pass12345')
        r = self.client.post(f'/api/v1/tasks/{self.task.id}/uncomplete/')
        self.assertEqual(r.status_code, 403)
