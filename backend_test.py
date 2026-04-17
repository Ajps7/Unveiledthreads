import requests
import sys
from datetime import datetime
import json
import io
import os

class UKStreetwearAPITester:
    def __init__(self, base_url="https://uk-streetwear-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_token = None
        self.brand_token = None
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, cookies=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers, cookies=cookies)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers, cookies=cookies)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers, cookies=cookies)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers, cookies=cookies)

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
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    'name': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'error': str(e)
            })
            return False, {}

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n=== TESTING AUTH ENDPOINTS ===")
        
        # Test user registration
        test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@test.com"
        success, response = self.run_test(
            "User Registration",
            "POST",
            "api/auth/register",
            200,
            data={
                "email": test_email,
                "password": "TestPass123!",
                "name": "Test User"
            }
        )
        if success:
            self.user_token = response.get('id')
        
        # Test admin login
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={
                "email": "admin@ukstreetwear.com",
                "password": "Admin123!"
            }
        )
        if success:
            self.admin_token = response.get('id')
        
        # Test brand login
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
        if success:
            self.brand_token = response.get('id')
        
        # Test auth/me endpoint
        self.run_test(
            "Get Current User",
            "GET",
            "api/auth/me",
            200
        )

    def test_categories_endpoint(self):
        """Test categories endpoint"""
        print("\n=== TESTING CATEGORIES ===")
        
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "api/categories",
            200
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            print(f"✅ Found {len(response)} categories")
        else:
            print("❌ Categories response invalid")

    def test_brands_endpoints(self):
        """Test brand-related endpoints"""
        print("\n=== TESTING BRANDS ENDPOINTS ===")
        
        # Get all brands
        success, brands = self.run_test(
            "Get All Brands",
            "GET",
            "api/brands",
            200
        )
        
        # Get boosted brands
        self.run_test(
            "Get Boosted Brands",
            "GET",
            "api/brands/boosted",
            200
        )
        
        # Get brand of the week
        success, bow = self.run_test(
            "Get Brand of Week",
            "GET",
            "api/brands/brand-of-week",
            200
        )
        
        # Test individual brand if we have brands
        if success and brands and len(brands) > 0:
            brand_id = brands[0].get('id')
            if brand_id:
                self.run_test(
                    "Get Individual Brand",
                    "GET",
                    f"api/brands/{brand_id}",
                    200
                )

    def test_products_endpoints(self):
        """Test product-related endpoints"""
        print("\n=== TESTING PRODUCTS ENDPOINTS ===")
        
        # Get all products
        success, products = self.run_test(
            "Get All Products",
            "GET",
            "api/products",
            200
        )
        
        # Test with search parameter
        self.run_test(
            "Search Products",
            "GET",
            "api/products?search=hoodie",
            200
        )
        
        # Test with category filter
        self.run_test(
            "Filter Products by Category",
            "GET",
            "api/products?category=hoodies",
            200
        )
        
        # Test individual product if we have products
        if success and products and len(products) > 0:
            product_id = products[0].get('id')
            if product_id:
                self.run_test(
                    "Get Individual Product",
                    "GET",
                    f"api/products/{product_id}",
                    200
                )

    def test_brand_application_flow(self):
        """Test brand application endpoints"""
        print("\n=== TESTING BRAND APPLICATION FLOW ===")
        
        # Test brand application (requires auth)
        test_application = {
            "brand_name": f"Test Brand {datetime.now().strftime('%H%M%S')}",
            "description": "A test streetwear brand for testing purposes",
            "location": "London",
            "category": "hoodies",
            "instagram_handle": "@testbrand",
            "website": "https://testbrand.com"
        }
        
        # This should fail without auth
        self.run_test(
            "Brand Application (No Auth)",
            "POST",
            "api/brands/apply",
            401,
            data=test_application
        )

    def test_admin_endpoints(self):
        """Test admin-only endpoints"""
        print("\n=== TESTING ADMIN ENDPOINTS ===")
        
        # Test admin stats (should fail without auth)
        self.run_test(
            "Admin Stats (No Auth)",
            "GET",
            "api/admin/stats",
            401
        )
        
        # Test admin applications (should fail without auth)
        self.run_test(
            "Admin Applications (No Auth)",
            "GET",
            "api/admin/applications",
            401
        )

    def test_boost_endpoints(self):
        """Test boost/payment endpoints"""
        print("\n=== TESTING BOOST ENDPOINTS ===")
        
        # Get boost packages
        success, packages = self.run_test(
            "Get Boost Packages",
            "GET",
            "api/boost/packages",
            200
        )
        
        if success and isinstance(packages, list) and len(packages) > 0:
            print(f"✅ Found {len(packages)} boost packages")
        else:
            print("❌ Boost packages response invalid")

    def test_image_upload_endpoints(self):
        """Test image upload endpoints"""
        print("\n=== TESTING IMAGE UPLOAD ENDPOINTS ===")
        
        # Test image upload without auth (should fail)
        self.run_test(
            "Image Upload (No Auth)",
            "POST",
            "api/upload/image",
            401
        )
        
        # Test brand logo upload without auth (should fail)
        self.run_test(
            "Brand Logo Upload (No Auth)",
            "POST",
            "api/brands/upload-logo",
            401
        )
        
        # Test brand banner upload without auth (should fail)
        self.run_test(
            "Brand Banner Upload (No Auth)",
            "POST",
            "api/brands/upload-banner",
            401
        )

    def test_orders_endpoints(self):
        """Test order-related endpoints"""
        print("\n=== TESTING ORDERS ENDPOINTS ===")
        
        # Test my orders without auth (should fail)
        self.run_test(
            "My Orders (No Auth)",
            "GET",
            "api/orders/my-orders",
            401
        )
        
        # Test brand orders without auth (should fail)
        self.run_test(
            "Brand Orders (No Auth)",
            "GET",
            "api/orders/brand-orders",
            401
        )
        
        # Test order checkout without auth (should fail)
        self.run_test(
            "Order Checkout (No Auth)",
            "POST",
            "api/orders/checkout",
            401,
            data={
                "product_id": "test_id",
                "size": "M",
                "origin_url": "https://test.com"
            }
        )

    def test_notifications_endpoints(self):
        """Test notification endpoints"""
        print("\n=== TESTING NOTIFICATIONS ENDPOINTS ===")
        
        # Test notifications without auth (should fail)
        self.run_test(
            "Get Notifications (No Auth)",
            "GET",
            "api/notifications",
            401
        )
        
        # Test unread count without auth (should fail)
        self.run_test(
            "Get Unread Count (No Auth)",
            "GET",
            "api/notifications/unread-count",
            401
        )

    def test_wishlist_endpoints(self):
        """Test wishlist endpoints"""
        print("\n=== TESTING WISHLIST ENDPOINTS ===")
        
        # Test wishlist without auth (should fail)
        self.run_test(
            "Get Wishlist (No Auth)",
            "GET",
            "api/wishlist",
            401
        )
        
        # Test wishlist IDs without auth (should fail)
        self.run_test(
            "Get Wishlist IDs (No Auth)",
            "GET",
            "api/wishlist/ids",
            401
        )
        
        # Test add to wishlist without auth (should fail)
        self.run_test(
            "Add to Wishlist (No Auth)",
            "POST",
            "api/wishlist/test_product_id",
            401
        )
        
        # Test remove from wishlist without auth (should fail)
        self.run_test(
            "Remove from Wishlist (No Auth)",
            "DELETE",
            "api/wishlist/test_product_id",
            401
        )

    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        print("\n=== TESTING ANALYTICS ENDPOINTS ===")
        
        # Test brand analytics without auth (should fail)
        self.run_test(
            "Get Brand Analytics (No Auth)",
            "GET",
            "api/analytics/brand",
            401
        )
        
        # Test product view tracking (should work without auth)
        self.run_test(
            "Track Product View",
            "POST",
            "api/analytics/view/test_product_id",
            200
        )

    def test_file_serving(self):
        """Test file serving endpoint"""
        print("\n=== TESTING FILE SERVING ===")
        
        # Test file serving with non-existent file (should return 404)
        self.run_test(
            "File Serving (Non-existent)",
            "GET",
            "api/files/non-existent-file.jpg",
            404
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting UK Streetwear Hub API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Test basic endpoints first
        self.test_categories_endpoint()
        self.test_brands_endpoints()
        self.test_products_endpoints()
        self.test_boost_endpoints()
        
        # Test new features
        self.test_wishlist_endpoints()
        self.test_analytics_endpoints()
        self.test_image_upload_endpoints()
        self.test_orders_endpoints()
        self.test_notifications_endpoints()
        self.test_file_serving()
        
        # Test auth endpoints
        self.test_auth_endpoints()
        
        # Test protected endpoints
        self.test_brand_application_flow()
        self.test_admin_endpoints()
        
        # Print final results
        print(f"\n📊 FINAL RESULTS:")
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
    tester = UKStreetwearAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())