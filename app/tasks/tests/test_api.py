from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from tasks.models import TeamList, Task

User = get_user_model()


class TaskApiPermissionsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.project = TeamList.objects.create(name='P1', created_by=self.owner)

    def test_create_task_forbidden_for_non_member(self):
        self.client.login(username='other', password='pass12345')
        payload = {
            'title': 'T1',
            'list': self.project.id,
        }
        r = self.client.post('/api/v1/tasks/', payload, format='json')
        self.assertEqual(r.status_code, 403)

    def test_create_task_allowed_for_owner(self):
        self.client.login(username='owner', password='pass12345')
        payload = {
            'title': 'T1',
            'list': self.project.id,
        }
        r = self.client.post('/api/v1/tasks/', payload, format='json')
        self.assertEqual(r.status_code, 201)

    def test_complete_task_requires_permission(self):
        task = Task.objects.create(
            title='T1',
            list=self.project,
            assigned_to=self.owner,
            created_by=self.owner,
        )
        self.client.login(username='other', password='pass12345')
        r = self.client.post(f'/api/v1/tasks/{task.id}/complete/')
        self.assertEqual(r.status_code, 403)

        self.client.login(username='owner', password='pass12345')
        r = self.client.post(f'/api/v1/tasks/{task.id}/complete/')
        self.assertEqual(r.status_code, 200)
