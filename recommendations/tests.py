from django.test import TestCase
from django.contrib.auth.models import User
from restaurants.models import Restaurant, Category, MenuItem
from orders.models import Cart, CartItem, Order, OrderItem
from recommendations.recommender import get_user_recommendations


def make_world():
    """Create a restaurant with 10 menu items for testing."""
    owner = User.objects.create_user(username='rec_owner', password='pass1234')
    owner.userprofile.role = 'OWNER'; owner.userprofile.save()
    rest = Restaurant.objects.create(owner=owner, name='RecResto', address='A', phone='1')
    cat  = Category.objects.create(restaurant=rest, name='Food')
    items = []
    for i in range(10):
        items.append(MenuItem.objects.create(
            restaurant=rest, category=cat,
            name=f'Dish {i+1}', price=100+i*10, available=True
        ))
    return rest, items


class RecommendationPhase1Test(TestCase):
    """Phase 1: personalized recommendations from user's own order history"""

    def setUp(self):
        self.rest, self.items = make_world()
        self.user = User.objects.create_user(username='rec_user1', password='pass1234')

    def test_returns_user_ordered_items(self):
        order = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=500)
        OrderItem.objects.create(order=order, menu_item=self.items[0], quantity=3)
        OrderItem.objects.create(order=order, menu_item=self.items[1], quantity=1)
        recs = get_user_recommendations(self.user, limit=5)
        rec_names = [r.name for r in recs]
        self.assertIn('Dish 1', rec_names)
        self.assertIn('Dish 2', rec_names)

    def test_most_ordered_item_ranked_first(self):
        for _ in range(5):
            o = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100)
            OrderItem.objects.create(order=o, menu_item=self.items[0], quantity=1)
        o = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100)
        OrderItem.objects.create(order=o, menu_item=self.items[1], quantity=1)
        recs = get_user_recommendations(self.user, limit=5)
        self.assertEqual(recs[0].name, 'Dish 1')  # ordered 5 times vs 1

    def test_limit_respected(self):
        for i in range(8):
            o = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100)
            OrderItem.objects.create(order=o, menu_item=self.items[i], quantity=1)
        recs = get_user_recommendations(self.user, limit=5)
        self.assertLessEqual(len(recs), 5)

    def test_returns_at_most_limit_items(self):
        recs = get_user_recommendations(self.user, limit=5)
        self.assertLessEqual(len(recs), 5)


class RecommendationPhase2Test(TestCase):
    """Phase 2: popularity fallback when user has < limit personal items"""

    def setUp(self):
        self.rest, self.items = make_world()
        self.user   = User.objects.create_user(username='rec_user2', password='pass1234')
        self.other  = User.objects.create_user(username='rec_other', password='pass1234')
        # Other user has ordered items[3] many times — makes it globally popular
        for _ in range(10):
            o = Order.objects.create(user=self.other, restaurant=self.rest, total_amount=100)
            OrderItem.objects.create(order=o, menu_item=self.items[3], quantity=1)

    def test_popular_items_fill_remaining_slots(self):
        # self.user has ordered only 1 item — needs 4 more from popular
        o = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100)
        OrderItem.objects.create(order=o, menu_item=self.items[0], quantity=1)
        recs = get_user_recommendations(self.user, limit=5)
        self.assertEqual(len(recs), 5)

    def test_globally_popular_item_included_when_personal_insufficient(self):
        o = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100)
        OrderItem.objects.create(order=o, menu_item=self.items[0], quantity=1)
        recs = get_user_recommendations(self.user, limit=5)
        rec_names = [r.name for r in recs]
        self.assertIn('Dish 4', rec_names)  # items[3] is globally popular

    def test_no_duplicate_in_recommendations(self):
        o = Order.objects.create(user=self.user, restaurant=self.rest, total_amount=100)
        OrderItem.objects.create(order=o, menu_item=self.items[3], quantity=1)
        recs = get_user_recommendations(self.user, limit=5)
        ids = [r.id for r in recs]
        self.assertEqual(len(ids), len(set(ids)))


class RecommendationPhase3Test(TestCase):
    """Phase 3: cold-start fallback for brand-new users with no order history"""

    def setUp(self):
        self.rest, self.items = make_world()
        self.new_user = User.objects.create_user(username='brand_new', password='pass1234')

    def test_new_user_gets_recommendations(self):
        recs = get_user_recommendations(self.new_user, limit=5)
        self.assertGreater(len(recs), 0)

    def test_cold_start_returns_up_to_limit(self):
        recs = get_user_recommendations(self.new_user, limit=5)
        self.assertLessEqual(len(recs), 5)

    def test_unavailable_items_excluded(self):
        for item in self.items:
            item.available = False; item.save()
        recs = get_user_recommendations(self.new_user, limit=5)
        for r in recs:
            self.assertTrue(r.available)

    def test_only_available_items_recommended(self):
        self.items[0].available = False; self.items[0].save()
        o = Order.objects.create(user=self.new_user, restaurant=self.rest, total_amount=100)
        OrderItem.objects.create(order=o, menu_item=self.items[0], quantity=5)
        recs = get_user_recommendations(self.new_user, limit=5)
        for r in recs:
            self.assertTrue(r.available)
