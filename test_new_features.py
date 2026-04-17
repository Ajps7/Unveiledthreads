import requests
import sys
from datetime import datetime
import json

class NewFeaturesAPITester:
    def __init__(self, base_url="https://uk-streetwear-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.user_cookies = None
        self.brand_cookies = None
        self.product_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.content else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:300]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'error': str(e)
            })
            return False, {}

    def login_as_buyer(self):
        """Login as test buyer"""
        print("\n=== LOGGING IN AS BUYER ===")
        success, response = self.run_test(
            "Buyer Login",
            "POST",
            "api/auth/login",
            200,
            data={
                "email": "buyer@test.com",
                "password": "Buyer123!"
            }
        )
        return success

    def login_as_brand(self):
        """Login as demo brand"""
        print("\n=== LOGGING IN AS BRAND ===")
        success, response = self.run_test(
            "Brand Login",
            "POST",
            "api/auth/login",
            200,
            data={
                "email": "demo@threadandbone.uk",
                "password": "Demo123!"
            }
        )
        return success

    def get_test_product_id(self):
        """Get a product ID for testing"""
        success, products = self.run_test(
            "Get Products for Testing",
            "GET",
            "api/products?limit=1",
            200
        )
        if success and products and len(products) > 0:
            self.product_id = products[0].get('id')
            print(f"✅ Using product ID: {self.product_id}")
            return True
        return False

    def test_wishlist_flow(self):
        """Test complete wishlist functionality"""
        print("\n=== TESTING WISHLIST FLOW ===")
        
        if not self.product_id:
            print("❌ No product ID available for wishlist testing")
            return
        
        # Test adding to wishlist
        success, response = self.run_test(
            "Add Product to Wishlist",
            "POST",
            f"api/wishlist/{self.product_id}",
            200
        )
        
        # Test getting wishlist
        success, wishlist = self.run_test(
            "Get User Wishlist",
            "GET",
            "api/wishlist",
            200
        )
        
        if success and isinstance(wishlist, list):
            print(f"✅ Wishlist contains {len(wishlist)} items")
        
        # Test getting wishlist IDs
        success, ids = self.run_test(
            "Get Wishlist IDs",
            "GET",
            "api/wishlist/ids",
            200
        )
        
        if success and isinstance(ids, list):
            print(f"✅ Wishlist IDs: {len(ids)} items")
        
        # Test removing from wishlist
        self.run_test(
            "Remove Product from Wishlist",
            "DELETE",
            f"api/wishlist/{self.product_id}",
            200
        )

    def test_analytics_flow(self):
        """Test analytics functionality"""
        print("\n=== TESTING ANALYTICS FLOW ===")
        
        if not self.product_id:
            print("❌ No product ID available for analytics testing")
            return
        
        # Test product view tracking (should work without auth)
        success, response = self.run_test(
            "Track Product View",
            "POST",
            f"api/analytics/view/{self.product_id}",
            200
        )
        
        # Login as brand to test analytics
        if self.login_as_brand():
            # Test brand analytics
            success, analytics = self.run_test(
                "Get Brand Analytics",
                "GET",
                "api/analytics/brand",
                200
            )
            
            if success and isinstance(analytics, dict):
                print(f"✅ Analytics data received:")
                print(f"   - Total views: {analytics.get('total_views', 0)}")
                print(f"   - Total orders: {analytics.get('total_orders', 0)}")
                print(f"   - Total revenue: £{analytics.get('total_revenue', 0)}")
                print(f"   - Conversion rate: {analytics.get('conversion_rate', 0)}%")
            
            # Test analytics with different periods
            self.run_test(
                "Get Brand Analytics (7 days)",
                "GET",
                "api/analytics/brand?days=7",
                200
            )
            
            self.run_test(
                "Get Brand Analytics (90 days)",
                "GET",
                "api/analytics/brand?days=90",
                200
            )

    def test_notifications_flow(self):
        """Test notifications functionality"""
        print("\n=== TESTING NOTIFICATIONS FLOW ===")
        
        # Test getting notifications
        success, notifications = self.run_test(
            "Get User Notifications",
            "GET",
            "api/notifications",
            200
        )
        
        if success and isinstance(notifications, list):
            print(f"✅ Found {len(notifications)} notifications")
        
        # Test getting unread count
        success, count_data = self.run_test(
            "Get Unread Notifications Count",
            "GET",
            "api/notifications/unread-count",
            200
        )
        
        if success and isinstance(count_data, dict):
            print(f"✅ Unread notifications: {count_data.get('count', 0)}")

    def run_all_tests(self):
        """Run all new feature tests"""
        print("🚀 Starting New Features API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Get a product ID for testing
        if not self.get_test_product_id():
            print("❌ Could not get product ID for testing")
            return False
        
        # Login as buyer and test wishlist
        if self.login_as_buyer():
            self.test_wishlist_flow()
            self.test_notifications_flow()
        
        # Test analytics (includes brand login)
        self.test_analytics_flow()
        
        # Print final results
        print(f"\n📊 NEW FEATURES TEST RESULTS:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
                print(f"  - {test['name']}: {error_msg}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = NewFeaturesAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())