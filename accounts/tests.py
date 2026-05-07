from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass1234')

    def test_profile_auto_created_by_signal(self):
        """Signal must auto-create UserProfile when User is created"""
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_default_role_is_customer(self):
        self.assertEqual(self.user.userprofile.role, 'CUSTOMER')

    def test_str_method(self):
        self.assertIn('testuser', str(self.user.userprofile))

    def test_role_can_be_updated(self):
        p = self.user.userprofile
        p.role = 'OWNER'; p.save(); p.refresh_from_db()
        self.assertEqual(p.role, 'OWNER')


class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('register')

    def test_register_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_register_valid_customer(self):
        res = self.client.post(self.url, {'username':'newuser','password':'securepass','role':'CUSTOMER','phone':'9876543210'})
        self.assertRedirects(res, reverse('customer_dashboard'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_valid_owner_redirects_to_owner_dashboard(self):
        res = self.client.post(self.url, {'username':'owneruser','password':'securepass','role':'OWNER','phone':''})
        self.assertRedirects(res, reverse('owner_dashboard'))

    def test_register_duplicate_username_shows_error(self):
        User.objects.create_user(username='existing', password='pass1234')
        res = self.client.post(self.url, {'username':'existing','password':'pass9999','role':'CUSTOMER'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'already exists')

    def test_register_short_password_shows_error(self):
        res = self.client.post(self.url, {'username':'shortpw','password':'abc','role':'CUSTOMER'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '6 characters')

    def test_register_empty_username_shows_error(self):
        res = self.client.post(self.url, {'username':'','password':'pass1234','role':'CUSTOMER'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'required')

    def test_logged_in_user_redirected_from_register(self):
        User.objects.create_user(username='already', password='pass1234')
        self.client.login(username='already', password='pass1234')
        res = self.client.get(self.url)
        self.assertRedirects(res, reverse('customer_dashboard'))


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('login')
        self.user = User.objects.create_user(username='loginuser', password='pass1234')

    def test_login_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_valid_customer_login_redirects(self):
        res = self.client.post(self.url, {'username':'loginuser','password':'pass1234'})
        self.assertRedirects(res, reverse('customer_dashboard'))

    def test_valid_owner_login_redirects_to_owner_dashboard(self):
        u = User.objects.create_user(username='ownerlogin', password='pass1234')
        u.userprofile.role = 'OWNER'; u.userprofile.save()
        res = self.client.post(self.url, {'username':'ownerlogin','password':'pass1234'})
        self.assertRedirects(res, reverse('owner_dashboard'))

    def test_wrong_password_shows_error(self):
        res = self.client.post(self.url, {'username':'loginuser','password':'wrongpass'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Invalid')

    def test_nonexistent_user_shows_error(self):
        res = self.client.post(self.url, {'username':'ghost','password':'pass1234'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Invalid')

    def test_already_logged_in_redirected_away_from_login(self):
        self.client.login(username='loginuser', password='pass1234')
        res = self.client.get(self.url)
        self.assertRedirects(res, reverse('customer_dashboard'))


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(username='logoutuser', password='pass1234')
        self.client.login(username='logoutuser', password='pass1234')

    def test_logout_redirects_to_login(self):
        self.assertRedirects(self.client.get(reverse('logout')), reverse('login'))

    def test_after_logout_protected_pages_redirect_to_login(self):
        self.client.get(reverse('logout'))
        res = self.client.get(reverse('customer_dashboard'))
        self.assertEqual(res.status_code, 302)


class AdminDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='adminuser', password='pass1234')
        self.admin.userprofile.role = 'ADMIN'; self.admin.userprofile.save()
        self.customer = User.objects.create_user(username='custuser', password='pass1234')

    def test_admin_can_view_dashboard(self):
        self.client.login(username='adminuser', password='pass1234')
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 200)

    def test_customer_cannot_access_admin_dashboard(self):
        self.client.login(username='custuser', password='pass1234')
        res = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(res, reverse('home'))

    def test_unauthenticated_redirected_from_admin_dashboard(self):
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 302)
