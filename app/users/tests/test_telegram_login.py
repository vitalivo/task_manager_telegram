from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import User, TelegramLoginToken


class TelegramWebLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass12345')

    def test_tg_login_success_one_time(self):
        token = TelegramLoginToken.issue_for_user(self.user, ttl_seconds=300)
        url = reverse('users:telegram_login', kwargs={'token': token.token})

        r1 = self.client.get(url)
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r1['Location'], '/')

        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

        r2 = self.client.get(url)
        self.assertEqual(r2.status_code, 400)

    def test_tg_login_expired(self):
        token = TelegramLoginToken.issue_for_user(self.user, ttl_seconds=1)
        token.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        token.save(update_fields=['expires_at'])

        url = reverse('users:telegram_login', kwargs={'token': token.token})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

    def test_tg_login_invalid(self):
        url = reverse('users:telegram_login', kwargs={'token': '00000000-0000-0000-0000-000000000000'})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)
