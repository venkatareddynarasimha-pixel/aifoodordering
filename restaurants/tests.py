from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from restaurants.models import Restaurant, Category, MenuItem


class MenuItemModelTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner1', password='pass1234')
        self.owner.userprofile.role = 'OWNER'; self.owner.userprofile.save()
        self.restaurant = Restaurant.objects.create(owner=self.owner, name='Test Resto', address='123 St', phone='9999999999')
        self.category  = Category.objects.create(restaurant=self.restaurant, name='Main Course')
        self.item = MenuItem.objects.create(restaurant=self.restaurant, category=self.category,
                                            name='Butter Chicken', price=280.0, description='Creamy curry', available=True)

    def test_str_returns_name(self):
        self.assertEqual(str(self.item), 'Butter Chicken')

    def test_default_available_true(self):
        self.assertTrue(self.item.available)

    def test_price_stored_correctly(self):
        self.assertEqual(self.item.price, 280.0)

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Main Course')

    def test_restaurant_str(self):
        self.assertEqual(str(self.restaurant), 'Test Resto')


class MenuListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        owner = User.objects.create_user(username='mowner', password='pass1234')
        owner.userprofile.role = 'OWNER'; owner.userprofile.save()
        self.restaurant = Restaurant.objects.create(owner=owner, name='R1', address='A', phone='1')
        self.cat = Category.objects.create(restaurant=self.restaurant, name='Starters')
        MenuItem.objects.create(restaurant=self.restaurant, category=self.cat, name='Samosa', price=50, available=True)
        MenuItem.objects.create(restaurant=self.restaurant, category=self.cat, name='Spring Roll', price=80, available=True)
        MenuItem.objects.create(restaurant=self.restaurant, category=self.cat, name='Hidden Item', price=100, available=False)

    def test_menu_page_loads(self):
        self.assertEqual(self.client.get(reverse('menu')).status_code, 200)

    def test_only_available_items_shown(self):
        res = self.client.get(reverse('menu'))
        self.assertContains(res, 'Samosa')
        self.assertNotContains(res, 'Hidden Item')

    def test_search_by_name(self):
        res = self.client.get(reverse('menu') + '?q=Samosa')
        self.assertContains(res, 'Samosa')
        self.assertNotContains(res, 'Spring Roll')

    def test_search_no_results(self):
        res = self.client.get(reverse('menu') + '?q=Pizza')
        self.assertNotContains(res, 'Samosa')

    def test_sort_price_low_to_high(self):
        res = self.client.get(reverse('menu') + '?sort=low')
        self.assertEqual(res.status_code, 200)
        items = list(res.context['items'])
        prices = [i.price for i in items]
        self.assertEqual(prices, sorted(prices))

    def test_sort_price_high_to_low(self):
        res = self.client.get(reverse('menu') + '?sort=high')
        items = list(res.context['items'])
        prices = [i.price for i in items]
        self.assertEqual(prices, sorted(prices, reverse=True))


class OwnerDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='dashowner', password='pass1234')
        self.owner.userprofile.role = 'OWNER'; self.owner.userprofile.save()
        self.customer = User.objects.create_user(username='cust', password='pass1234')

    def test_owner_can_access_dashboard(self):
        self.client.login(username='dashowner', password='pass1234')
        self.assertEqual(self.client.get(reverse('owner_dashboard')).status_code, 200)

    def test_customer_cannot_access_owner_dashboard(self):
        self.client.login(username='cust', password='pass1234')
        res = self.client.get(reverse('owner_dashboard'))
        self.assertRedirects(res, reverse('home'))

    def test_unauthenticated_redirected(self):
        self.assertEqual(self.client.get(reverse('owner_dashboard')).status_code, 302)


class AddMenuItemTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='itemowner', password='pass1234')
        self.owner.userprofile.role = 'OWNER'; self.owner.userprofile.save()
        self.restaurant = Restaurant.objects.create(owner=self.owner, name='MyResto', address='A', phone='1')
        self.category = Category.objects.create(restaurant=self.restaurant, name='Mains')
        self.client.login(username='itemowner', password='pass1234')

    def test_add_item_page_loads(self):
        self.assertEqual(self.client.get(reverse('add_menu_item')).status_code, 200)

    def test_add_valid_item(self):
        res = self.client.post(reverse('add_menu_item'), {
            'name': 'Dal Makhani', 'description': 'Rich lentil curry',
            'price': '180', 'restaurant': self.restaurant.id, 'category': self.category.id
        })
        self.assertRedirects(res, reverse('owner_dashboard'))
        self.assertTrue(MenuItem.objects.filter(name='Dal Makhani').exists())

    def test_add_item_missing_name_shows_error(self):
        res = self.client.post(reverse('add_menu_item'), {
            'name': '', 'price': '100',
            'restaurant': self.restaurant.id, 'category': self.category.id
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'required')

    def test_toggle_item_availability(self):
        item = MenuItem.objects.create(restaurant=self.restaurant, category=self.category,
                                       name='Toggle Me', price=100, available=True)
        self.client.get(reverse('toggle_item', args=[item.id]))
        item.refresh_from_db()
        self.assertFalse(item.available)
        self.client.get(reverse('toggle_item', args=[item.id]))
        item.refresh_from_db()
        self.assertTrue(item.available)

    def test_customer_cannot_add_menu_item(self):
        cust = User.objects.create_user(username='cust2', password='pass1234')
        self.client.logout()
        self.client.login(username='cust2', password='pass1234')
        res = self.client.get(reverse('add_menu_item'))
        self.assertRedirects(res, reverse('home'))
