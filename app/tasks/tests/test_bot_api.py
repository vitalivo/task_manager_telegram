from django.test import TestCase
from django.utils import timezone

from users.models import User
from tasks.models import TeamList, Task, ProjectMember


class BotApiEndpointsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bot_user', password='pass12345')
        self.other = User.objects.create_user(username='other_user', password='pass12345')
        self.profile = self.user.profile
        self.profile.telegram_chat_id = '123456'
        self.profile.save()
        self.project = TeamList.objects.create(name='P1', created_by=self.other)
        self.task = Task.objects.create(
            title='T1',
            list=self.project,
            assigned_to=self.user,
            created_by=self.user,
        )
        ProjectMember.objects.create(
            project=self.project,
            user=self.user,
            role=ProjectMember.Role.EXECUTOR,
        )

    def test_bot_task_set_status(self):
        r = self.client.post('/api/bot/task-set-status/', {
            'chat_id': self.profile.telegram_chat_id,
            'task_id': self.task.id,
            'status': Task.Status.DONE,
        })
        self.assertEqual(r.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)

    def test_bot_me(self):
        r = self.client.get('/api/bot/me/', {'chat_id': self.profile.telegram_chat_id})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get('linked'))

    def test_bot_get_user_tasks(self):
        r = self.client.get('/api/bot/get_user_tasks/', {'chat_id': self.profile.telegram_chat_id})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.task.id)

    def test_bot_task_comment(self):
        r = self.client.post('/api/bot/task-comment/', {
            'chat_id': self.profile.telegram_chat_id,
            'task_id': self.task.id,
            'text': 'Test comment',
        })
        self.assertEqual(r.status_code, 200)

    def test_bot_today(self):
        now = timezone.now()
        self.task.due_date = now
        self.task.save(update_fields=['due_date'])
        r = self.client.get('/api/bot/today/', {'chat_id': self.profile.telegram_chat_id})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(len(data) >= 1)

    def test_bot_project_set_status_requires_manager(self):
        r = self.client.post('/api/bot/project-set-status/', {
            'chat_id': self.profile.telegram_chat_id,
            'project_id': self.project.id,
            'status': TeamList.ProjectStatus.DONE,
        })
        self.assertEqual(r.status_code, 403)

        ProjectMember.objects.filter(
            project=self.project,
            user=self.user,
        ).update(role=ProjectMember.Role.MANAGER)
        r = self.client.post('/api/bot/project-set-status/', {
            'chat_id': self.profile.telegram_chat_id,
            'project_id': self.project.id,
            'status': TeamList.ProjectStatus.DONE,
        })
        self.assertEqual(r.status_code, 200)
