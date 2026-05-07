from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from restaurants.models import Restaurant, Category, MenuItem
from orders.models import Cart, CartItem, Order, OrderItem, Favorite


def make_owner_and_item(username='owner_x'):
    owner = User.objects.create_user(username=username, password='pass1234')
    owner.userprofile.role = 'OWNER'; owner.userprofile.save()
    rest  = Restaurant.objects.create(owner=owner, name='Resto', address='A', phone='1')
    cat   = Category.objects.create(restaurant=rest, name='Cat')
    item  = MenuItem.objects.create(restaurant=rest, category=cat, name='Dish', price=100.0, available=True)
    return owner, rest, cat, item


# ── Model Tests ──────────────────────────────────────────────────────────────
class CartItemModelTest(TestCase):
    def test_total_price(self):
        _, _, _, item = make_owner_and_item('o_cart')
        user  = User.objects.create_user(username='cust_cart', password='pass1234')
        cart  = Cart.objects.create(user=user)
        ci    = CartItem.objects.create(cart=cart, menu_item=item, quantity=3)
        self.assertEqual(ci.total_price(), 300.0)

    def test_total_price_quantity_one(self):
        _, _, _, item = make_owner_and_item('o_cart2')
        user = User.objects.create_user(username='cust_cart2', password='pass1234')
        cart = Cart.objects.create(user=user)
        ci   = CartItem.objects.create(cart=cart, menu_item=item, quantity=1)
        self.assertEqual(ci.total_price(), 100.0)


class OrderItemModelTest(TestCase):
    def test_item_total(self):
        owner, rest, _, item = make_owner_and_item('o_oi')
        user  = User.objects.create_user(username='cust_oi', password='pass1234')
        order = Order.objects.create(user=user, restaurant=rest, total_amount=200.0)
        oi    = OrderItem.objects.create(order=order, menu_item=item, quantity=2)
        self.assertEqual(oi.item_total(), 200.0)

    def test_order_str(self):
        _, rest, _, _ = make_owner_and_item('o_str')
        user  = User.objects.create_user(username='cust_str', password='pass1234')
        order = Order.objects.create(user=user, restaurant=rest, total_amount=100.0)
        self.assertIn(str(order.id), str(order))

    def test_order_default_status_is_pending(self):
        _, rest, _, _ = make_owner_and_item('o_def')
        user  = User.objects.create_user(username='cust_def', password='pass1234')
        order = Order.objects.create(user=user, restaurant=rest, total_amount=50.0)
        self.assertEqual(order.status, 'PENDING')


class FavoriteModelTest(TestCase):
    def test_favorite_created(self):
        _, _, _, item = make_owner_and_item('o_fav')
        user = User.objects.create_user(username='cust_fav', password='pass1234')
        fav, created = Favorite.objects.get_or_create(user=user, menu_item=item)
        self.assertTrue(created)

    def test_favorite_unique_together(self):
        _, _, _, item = make_owner_and_item('o_fav2')
        user = User.objects.create_user(username='cust_fav2', password='pass1234')
        Favorite.objects.create(user=user, menu_item=item)
        _, created = Favorite.objects.get_or_create(user=user, menu_item=item)
        self.assertFalse(created)  # second call does not create duplicate


# ── Cart View Tests ──────────────────────────────────────────────────────────
class CartViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        _, _, _, self.item = make_owner_and_item('o_cv')
        self.user = User.objects.create_user(username='cust_cv', password='pass1234')
        self.client.login(username='cust_cv', password='pass1234')

    def test_cart_page_loads(self):
        self.assertEqual(self.client.get(reverse('view_cart')).status_code, 200)

    def test_add_new_item_creates_cart_item_qty_1(self):
        self.client.get(reverse('add_to_cart', args=[self.item.id]))
        ci = CartItem.objects.get(cart__user=self.user, menu_item=self.item)
        self.assertEqual(ci.quantity, 1)

    def test_add_same_item_twice_increments_quantity(self):
        self.client.get(reverse('add_to_cart', args=[self.item.id]))
        self.client.get(reverse('add_to_cart', args=[self.item.id]))
        ci = CartItem.objects.get(cart__user=self.user, menu_item=self.item)
        self.assertEqual(ci.quantity, 2)

    def test_increase_cart_item_quantity(self):
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        self.client.post(reverse('update_cart_quantity', args=[ci.id]), {'action': 'increase'})
        ci.refresh_from_db()
        self.assertEqual(ci.quantity, 2)

    def test_decrease_cart_item_quantity(self):
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=3)
        self.client.post(reverse('update_cart_quantity', args=[ci.id]), {'action': 'decrease'})
        ci.refresh_from_db()
        self.assertEqual(ci.quantity, 2)

    def test_decrease_quantity_to_zero_removes_item(self):
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        self.client.post(reverse('update_cart_quantity', args=[ci.id]), {'action': 'decrease'})
        self.assertFalse(CartItem.objects.filter(id=ci.id).exists())

    def test_remove_from_cart(self):
        cart = Cart.objects.create(user=self.user)
        ci = CartItem.objects.create(cart=cart, menu_item=self.item, quantity=2)
        self.client.post(reverse('remove_from_cart', args=[ci.id]))
        self.assertFalse(CartItem.objects.filter(id=ci.id).exists())

    def test_cart_shows_correct_total(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, menu_item=self.item, quantity=3)
        res = self.client.get(reverse('view_cart'))
        self.assertContains(res, '300')

    def test_unauthenticated_cart_redirects_to_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('view_cart')).status_code, 302)


# ── Order View Tests ─────────────────────────────────────────────────────────
class PlaceOrderViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        _, self.rest, _, self.item = make_owner_and_item('o_po')
        self.user = User.objects.create_user(username='cust_po', password='pass1234')
        self.client.login(username='cust_po', password='pass1234')

    def test_place_order_creates_order(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, menu_item=self.item, quantity=2)
        self.client.get(reverse('place_order'))
        self.assertTrue(Order.objects.filter(user=self.user).exists())

    def test_place_order_clears_cart(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        self.client.get(reverse('place_order'))
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    def test_place_order_calculates_correct_total(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, menu_item=self.item, quantity=3)
        self.client.get(reverse('place_order'))
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.total_amount, 300.0)

    def test_place_order_creates_order_items(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, menu_item=self.item, quantity=2)
        self.client.get(reverse('place_order'))
        order = Order.objects.get(user=self.user)
        self.assertEqual(OrderItem.objects.filter(order=order).count(), 1)
        oi = OrderItem.objects.get(order=order)
        self.assertEqual(oi.quantity, 2)

    def test_place_order_empty_cart_redirects(self):
        res = self.client.get(reverse('place_order'))
        self.assertRedirects(res, reverse('view_cart'))

    def test_order_success_page_shown(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, menu_item=self.item, quantity=1)
        res = self.client.get(reverse('place_order'))
        self.assertTemplateUsed(res, 'order_success.html')


class MyOrdersViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        _, self.rest, _, _ = make_owner_and_item('o_mo')
        self.user = User.objects.create_user(username='cust_mo', password='pass1234')
        self.client.login(username='cust_mo', password='pass1234')
        Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100, status='PENDING')
        Order.objects.create(user=self.user, restaurant=self.rest, total_amount=200, status='DELIVERED')

    def test_my_orders_page_loads(self):
        self.assertEqual(self.client.get(reverse('my_orders')).status_code, 200)

    def test_all_orders_shown_by_default(self):
        res = self.client.get(reverse('my_orders'))
        self.assertEqual(res.context['orders'].count(), 2)

    def test_filter_by_pending(self):
        res = self.client.get(reverse('my_orders') + '?status=PENDING')
        self.assertEqual(res.context['orders'].count(), 1)
        self.assertEqual(res.context['orders'].first().status, 'PENDING')

    def test_filter_by_delivered(self):
        res = self.client.get(reverse('my_orders') + '?status=DELIVERED')
        self.assertEqual(res.context['orders'].count(), 1)
        self.assertEqual(res.context['orders'].first().status, 'DELIVERED')

    def test_invalid_filter_shows_all(self):
        res = self.client.get(reverse('my_orders') + '?status=INVALID')
        self.assertEqual(res.context['orders'].count(), 2)

    def test_other_user_orders_not_shown(self):
        other = User.objects.create_user(username='other_mo', password='pass1234')
        Order.objects.create(user=other, restaurant=self.rest, total_amount=999, status='PENDING')
        res = self.client.get(reverse('my_orders'))
        self.assertEqual(res.context['orders'].count(), 2)


# ── Favorites View Tests ─────────────────────────────────────────────────────
class FavoritesViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        _, _, _, self.item = make_owner_and_item('o_fv')
        self.user = User.objects.create_user(username='cust_fv', password='pass1234')
        self.client.login(username='cust_fv', password='pass1234')

    def test_favorites_page_loads(self):
        self.assertEqual(self.client.get(reverse('favorites')).status_code, 200)

    def test_add_favorite(self):
        self.client.get(reverse('add_favorite', args=[self.item.id]))
        self.assertTrue(Favorite.objects.filter(user=self.user, menu_item=self.item).exists())

    def test_add_favorite_duplicate_no_error(self):
        self.client.get(reverse('add_favorite', args=[self.item.id]))
        self.client.get(reverse('add_favorite', args=[self.item.id]))
        self.assertEqual(Favorite.objects.filter(user=self.user, menu_item=self.item).count(), 1)

    def test_remove_favorite(self):
        fav = Favorite.objects.create(user=self.user, menu_item=self.item)
        self.client.post(reverse('remove_favorite', args=[fav.id]))
        self.assertFalse(Favorite.objects.filter(id=fav.id).exists())

    def test_favorites_list_shows_only_current_user_items(self):
        other = User.objects.create_user(username='other_fv', password='pass1234')
        Favorite.objects.create(user=self.user, menu_item=self.item)
        _, _, _, other_item = make_owner_and_item('o_fv2')
        Favorite.objects.create(user=other, menu_item=other_item)
        res = self.client.get(reverse('favorites'))
        self.assertEqual(res.context['favorites'].count(), 1)


# ── Customer Dashboard Tests ─────────────────────────────────────────────────
class CustomerDashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cust_db', password='pass1234')
        self.client.login(username='cust_db', password='pass1234')

    def test_dashboard_loads(self):
        self.assertEqual(self.client.get(reverse('customer_dashboard')).status_code, 200)

    def test_dashboard_contains_recommended_items_key(self):
        res = self.client.get(reverse('customer_dashboard'))
        self.assertIn('recommended_items', res.context)

    def test_dashboard_unauthenticated_redirects(self):
        self.client.logout()
        res = self.client.get(reverse('customer_dashboard'))
        self.assertEqual(res.status_code, 302)
