from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

class AuthAPITests(APITestCase):
    def setUp(self):
        # Create a regular user
        self.user_password = 'testpassword123'
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password=self.user_password
        )

        # Create an admin user
        self.admin_password = 'testpassword123'
        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='testadmin@example.com',
            password=self.admin_password,
            role='admin'
        )

        # URLS
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.logout_url = reverse('auth-logout')
        self.user_url = reverse('auth-user')
        self.admin_users_list_url = reverse('admin-user-list')

    def test_user_registration_success(self):
        """
        Ensure a new user can be registered.
        """
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(User.objects.latest('id').username, 'newuser')

    def test_user_registration_duplicate_email(self):
        """
        Ensure registration fails if the email is already in use.
        """
        data = {
            'username': 'anotheruser',
            'email': 'testuser@example.com',  # Existing email
            'password': 'newpassword123'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_success(self):
        """
        Ensure a user can log in and a session is created.
        """
        data = {'username': self.user.username, 'password': self.user_password}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        # After login, the client should be authenticated
        response = self.client.get(self.user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)

    def test_user_login_fail(self):
        """
        Ensure login fails with incorrect credentials.
        """
        data = {'username': self.user.username, 'password': 'wrongpassword'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unable to log in', response.data['detail'])

    def test_user_logout(self):
        """
        Ensure a logged-in user can log out.
        """
        self.client.login(username=self.user.username, password=self.user_password)
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # After logout, accessing a protected endpoint should fail
        response = self.client.get(self.user_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_access(self):
        """
        Ensure unauthenticated users cannot access protected endpoints.
        """
        response = self.client.get(self.user_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class AdminAPITests(APITestCase):
    def setUp(self):
        self.user_password = 'testpassword123'
        self.user = User.objects.create_user(username='testuser', password=self.user_password)
        self.admin_password = 'testpassword123'
        self.admin_user = User.objects.create_user(username='testadmin', password=self.admin_password, role='admin')
        self.admin_users_list_url = reverse('admin-user-list')

    def test_admin_access_by_anon(self):
        """
        Ensure anonymous users cannot access admin endpoints.
        """
        response = self.client.get(self.admin_users_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_access_by_regular_user(self):
        """
        Ensure regular users cannot access admin endpoints.
        """
        self.client.login(username=self.user.username, password=self.user_password)
        response = self.client.get(self.admin_users_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_access_by_admin_user(self):
        """
        Ensure admin users can access admin endpoints.
        """
        self.client.login(username=self.admin_user.username, password=self.admin_password)
        response = self.client.get(self.admin_users_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The response should contain a list of all users
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)

class RateLimitingTests(APITestCase):
    def test_login_rate_limit(self):
        """
        Ensure the login view is rate-limited.
        """
        # The rate is '10/hour'
        url = reverse('auth-login')
        data = {'username': 'test', 'password': 'testpassword'}

        # Exhaust the rate limit
        for i in range(10):
            response = self.client.post(url, data, format='json')
            # It will fail due to bad credentials, but that's fine. It still counts as a request.
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # The 11th request should be throttled
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
