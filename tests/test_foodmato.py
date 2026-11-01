import unittest
import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from foodMenuWebsite import app, db, bcrypt, login_manager
from foodMenuWebsite.models import User, Restaurant, MenuItem, Order, OrderItem, OrderStatusHistory, RestaurantReview, Cart
from foodMenuWebsite.ai_assistant import haversine_distance, generate_ai_response, build_knowledge_context

class FoodmatoPlatformTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        login_manager.session_protection = None
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def login_as(self, user_id):
        self.client.get('/logout', follow_redirects=True)
        user = db.session.get(User, user_id)
        if user:
            self.client.post('/login', data={'email': user.email, 'password': 'Password123'}, follow_redirects=True)

    # -------------------------------------------------------------
    # 1. Database & Seed Data Tests
    # -------------------------------------------------------------
    def test_database_records_exist(self):
        """Verify that existing database data was preserved and augmented."""
        users_count = User.query.count()
        menu_count = MenuItem.query.count()
        rest_count = Restaurant.query.count()
        order_count = Order.query.count()

        self.assertGreaterEqual(users_count, 6, "All 6 original users must exist")
        self.assertGreaterEqual(menu_count, 150, "All original menu items must exist")
        self.assertGreaterEqual(rest_count, 8, "8 Hyderabad restaurants must be seeded")
        self.assertGreaterEqual(order_count, 9, "Original orders must be preserved")

    # -------------------------------------------------------------
    # 2. Smart Food Filters Tests
    # -------------------------------------------------------------
    def test_smart_filters_category(self):
        """Test filtering by food category."""
        response = self.client.get('/menu?category=pizza')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Margherita Pizza', response.data)

    def test_smart_filters_veg(self):
        """Test filtering by vegetarian only."""
        response = self.client.get('/menu?veg=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pure Vegetarian', response.data)

    def test_smart_filters_non_veg(self):
        """Test filtering by non-vegetarian only."""
        response = self.client.get('/menu?veg=0')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Non-Vegetarian', response.data)

    def test_smart_filters_spicy(self):
        """Test filtering by spicy dishes only."""
        response = self.client.get('/menu?spicy=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Spicy', response.data)

    def test_smart_filters_price_range(self):
        """Test filtering by min and max price."""
        response = self.client.get('/menu?min_price=5&max_price=9')
        self.assertEqual(response.status_code, 200)

    def test_smart_filters_sorting(self):
        """Test price and rating sorting."""
        response = self.client.get('/menu?sort=price_asc')
        self.assertEqual(response.status_code, 200)
        response_desc = self.client.get('/menu?sort=price_desc')
        self.assertEqual(response_desc.status_code, 200)
        response_rating = self.client.get('/menu?sort=rating_desc')
        self.assertEqual(response_rating.status_code, 200)

    def test_food_detail_page(self):
        """Test individual food item detail page."""
        # Unauthenticated: shows login prompt
        item = MenuItem.query.first()
        self.assertIsNotNone(item)
        response = self.client.get(f'/food/{item.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(item.name.encode('utf-8'), response.data)
        self.assertIn(b'Log in to Order This Dish', response.data)

        # Authenticated: shows Add to Cart
        with self.client:
            self.login_as(2)
            res_auth = self.client.get(f'/food/{item.id}')
            self.assertEqual(res_auth.status_code, 200)
            self.assertIn(b'Add to Cart', res_auth.data)

    # -------------------------------------------------------------
    # 3. GPS & Haversine Distance Tests
    # -------------------------------------------------------------
    def test_haversine_formula(self):
        """Test accurate great-circle distance computation in kilometers."""
        # Jubilee Hills (17.4334, 78.4072) to Secunderabad (17.4411, 78.4870)
        dist = haversine_distance(17.4334, 78.4072, 17.4411, 78.4870)
        self.assertGreater(dist, 7.0)
        self.assertLess(dist, 10.0)

    def test_nearby_restaurants_api(self):
        """Test nearby restaurants JSON endpoint with distance calculation."""
        response = self.client.get('/api/restaurants/nearby?lat=17.4401&lng=78.3489&max_distance=10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('restaurants', data)
        self.assertGreater(len(data['restaurants']), 0)
        if len(data['restaurants']) >= 2:
            self.assertLessEqual(data['restaurants'][0]['distance_km'], data['restaurants'][1]['distance_km'])

    def test_restaurants_view(self):
        """Test restaurants listing directory view."""
        response = self.client.get('/restaurants')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Discover Nearby Restaurants', response.data)
        self.assertIn(b'Find Restaurants Near Me', response.data)

    # -------------------------------------------------------------
    # 4. Cart & Checkout Flow Tests
    # -------------------------------------------------------------
    def test_cart_and_checkout(self):
        """Test adding item to cart, viewing cart, and placing order."""
        item = MenuItem.query.first()
        self.assertIsNotNone(item)
        with self.client:
            self.login_as(2)

            # Add item to cart
            add_res = self.client.post(f'/cart/add/{item.id}', data={'quantity': 2}, follow_redirects=True)
            self.assertEqual(add_res.status_code, 200)

            # Verify cart view
            cart_res = self.client.get('/cart')
            self.assertEqual(cart_res.status_code, 200)
            self.assertIn(item.name.encode('utf-8'), cart_res.data)

            # Perform checkout
            checkout_res = self.client.post('/checkout', data={
                'delivery_address': 'Flat 101, Test Road, Pune',
                'phone': '+91 99999 11111'
            }, follow_redirects=True)
            self.assertEqual(checkout_res.status_code, 200)
            self.assertIn(b'Live Order Tracking', checkout_res.data)

    # -------------------------------------------------------------
    # 5. Live Order Tracking Tests
    # -------------------------------------------------------------
    def test_order_tracking_page_and_api(self):
        """Test dedicated order tracking page and live polling endpoint."""
        order = db.session.get(Order, 2)
        self.assertIsNotNone(order)

        with self.client:
            self.login_as(2)

            # Tracking page
            response = self.client.get(f'/order/{order.id}/track')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Live Order Tracking', response.data)
            self.assertIn(b'Order Progress', response.data)

            # JSON Polling endpoint
            api_res = self.client.get(f'/api/order/{order.id}/status')
            self.assertEqual(api_res.status_code, 200)
            poll_data = json.loads(api_res.data)
            self.assertEqual(poll_data['order_id'], order.id)
            self.assertIn('status', poll_data)
            self.assertIn('history', poll_data)

    # -------------------------------------------------------------
    # 6. Restaurant Ratings & Verified Reviews Tests
    # -------------------------------------------------------------
    def test_reviews_page(self):
        """Test public customer reviews page loads DB data."""
        response = self.client.get('/reviews')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'What Food Lovers Say', response.data)

    def test_restaurant_detail_and_reviews(self):
        """Test restaurant page includes ratings, map, and menu."""
        response = self.client.get('/restaurant/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Paradise Biryani', response.data)
        self.assertIn(b'Customer Reviews', response.data)
        self.assertIn(b'Restaurant Location', response.data)

    # -------------------------------------------------------------
    # 7. AI Chatbot Assistant Tests
    # -------------------------------------------------------------
    def test_chatbot_context_grounding(self):
        """Verify context generation extracts real DB entities."""
        context = build_knowledge_context("Suggest food under $10", user_id=2, user_lat=17.44, user_lng=78.34)
        self.assertIn("MATCHING FOOD ITEMS", context)
        self.assertIn("NEARBY RESTAURANTS", context)

    def test_chatbot_api_endpoint(self):
        """Verify chatbot endpoint returns grounded response."""
        payload = {
            'message': 'Find restaurants near me',
            'latitude': 17.4401,
            'longitude': 78.3489
        }
        response = self.client.post('/api/chat', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('response', data)
        self.assertTrue(len(data['response']) > 10)

    # -------------------------------------------------------------
    # 8. Admin Dashboard Access Control
    # -------------------------------------------------------------
    def test_admin_access_control(self):
        """Regular customer cannot access admin dashboard; owner can."""
        # Non-logged in
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)  # Redirects to login

        # Logged in as regular customer (user #2 is_owner=False)
        with self.client:
            self.login_as(2)
            response = self.client.get('/admin')
            self.assertEqual(response.status_code, 302)  # Redirects to home with flash

        # Logged in as owner (user #1 is_owner=True)
        with self.client:
            self.login_as(1)
            response = self.client.get('/admin')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Admin Executive Dashboard', response.data)

    def test_owner_orders_management(self):
        """Owner can view and update order status."""
        with self.client:
            self.login_as(1)
            response = self.client.get('/owner/orders')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Orders Management', response.data)

if __name__ == '__main__':
    unittest.main()
