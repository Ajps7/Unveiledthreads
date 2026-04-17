import requests
import sys
from datetime import datetime
import json

class ReviewsShippingTester:
    def __init__(self, base_url="https://uk-streetwear-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_cookies = None
        self.brand_cookies = None
        self.buyer_cookies = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_product_id = None
        self.test_order_id = None
        self.test_brand_id = None

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

    def setup_auth(self):
        """Setup authentication for different user types"""
        print("\n=== SETTING UP AUTHENTICATION ===")
        
        # Login as admin
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
            self.admin_cookies = self.session.cookies.copy()
            print("✅ Admin authenticated")
        
        # Login as brand
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
            self.brand_cookies = self.session.cookies.copy()
            print("✅ Brand authenticated")
        
        # Register and login as buyer
        test_email = f"buyer_test_{datetime.now().strftime('%H%M%S')}@test.com"
        success, response = self.run_test(
            "Buyer Registration",
            "POST",
            "api/auth/register",
            200,
            data={
                "email": test_email,
                "password": "Buyer123!",
                "name": "Test Buyer"
            }
        )
        if success:
            self.buyer_cookies = self.session.cookies.copy()
            print("✅ Buyer registered and authenticated")

    def test_shipping_couriers(self):
        """Test shipping couriers endpoint"""
        print("\n=== TESTING SHIPPING COURIERS ===")
        
        success, response = self.run_test(
            "GET /api/shipping/couriers",
            "GET",
            "api/shipping/couriers",
            200
        )
        
        if success and isinstance(response, list):
            print(f"✅ Found {len(response)} UK couriers")
            expected_couriers = ["Royal Mail", "Evri", "DPD", "Yodel", "UPS", "FedEx"]
            for courier in expected_couriers:
                if courier in response:
                    print(f"  ✓ {courier} found")
                else:
                    print(f"  ⚠️ {courier} missing")
        else:
            print("❌ Invalid couriers response")

    def test_product_with_shipping_cost(self):
        """Test creating product with shipping cost"""
        print("\n=== TESTING PRODUCT WITH SHIPPING COST ===")
        
        if not self.brand_cookies:
            print("❌ Brand authentication required")
            return
        
        # Create product with shipping cost
        product_data = {
            "name": f"Test Hoodie {datetime.now().strftime('%H%M%S')}",
            "description": "Test hoodie with shipping cost",
            "price": 49.99,
            "category": "hoodies",
            "sizes": ["S", "M", "L"],
            "images": [],
            "stock": 10,
            "shipping_cost": 5.99
        }
        
        success, response = self.run_test(
            "Create Product with Shipping Cost",
            "POST",
            "api/products",
            200,
            data=product_data,
            cookies=self.brand_cookies
        )
        
        if success and response.get('id'):
            self.test_product_id = response['id']
            print(f"✅ Product created with ID: {self.test_product_id}")
            print(f"✅ Shipping cost: £{response.get('shipping_cost', 0)}")
        
        # Verify product details include shipping cost
        if self.test_product_id:
            success, product = self.run_test(
                "Get Product with Shipping Cost",
                "GET",
                f"api/products/{self.test_product_id}",
                200
            )
            
            if success and product.get('shipping_cost') == 5.99:
                print("✅ Product shipping cost verified")
            else:
                print("❌ Product shipping cost not found or incorrect")

    def test_reviews_endpoints(self):
        """Test reviews endpoints"""
        print("\n=== TESTING REVIEWS ENDPOINTS ===")
        
        if not self.test_product_id:
            print("❌ Test product required for reviews testing")
            return
        
        # Test get product reviews (should work even with no reviews)
        success, response = self.run_test(
            "GET /api/reviews/product/{id}",
            "GET",
            f"api/reviews/product/{self.test_product_id}",
            200
        )
        
        if success:
            print(f"✅ Product reviews response: {response.get('count', 0)} reviews")
            print(f"✅ Avg product rating: {response.get('avg_product_rating', 0)}")
            print(f"✅ Avg brand rating: {response.get('avg_brand_rating', 0)}")
        
        # Get brand ID for brand reviews test
        if success and self.test_product_id:
            success, product = self.run_test(
                "Get Product for Brand ID",
                "GET",
                f"api/products/{self.test_product_id}",
                200
            )
            if success and product.get('brand_id'):
                self.test_brand_id = product['brand_id']
        
        # Test get brand reviews
        if self.test_brand_id:
            success, response = self.run_test(
                "GET /api/reviews/brand/{id}",
                "GET",
                f"api/reviews/brand/{self.test_brand_id}",
                200
            )
            
            if success:
                print(f"✅ Brand reviews response: {response.get('count', 0)} reviews")
        
        # Test creating review without order (should fail)
        if self.buyer_cookies:
            success, response = self.run_test(
                "Create Review without Order",
                "POST",
                "api/reviews",
                404,  # Should fail - no order found
                data={
                    "order_id": "507f1f77bcf86cd799439011",  # Valid ObjectId format but non-existent
                    "product_rating": 5,
                    "brand_rating": 4,
                    "comment": "Great product!"
                },
                cookies=self.buyer_cookies
            )

    def test_order_shipping_flow(self):
        """Test order shipping workflow"""
        print("\n=== TESTING ORDER SHIPPING FLOW ===")
        
        if not self.test_product_id or not self.brand_cookies:
            print("❌ Test product and brand authentication required")
            return
        
        # Note: We can't easily test the full order flow without Stripe integration
        # But we can test the shipping endpoints with mock data
        
        # Test shipping order without valid order (should fail)
        success, response = self.run_test(
            "Ship Order (Invalid Order)",
            "PUT",
            "api/orders/507f1f77bcf86cd799439011/ship",  # Valid ObjectId format but non-existent
            404,  # Order not found
            data={
                "tracking_number": "RM123456789GB",
                "courier": "Royal Mail"
            },
            cookies=self.brand_cookies
        )
        
        # Test update shipping status without valid order (should fail)
        success, response = self.run_test(
            "Update Shipping Status (Invalid Order)",
            "PUT",
            "api/orders/507f1f77bcf86cd799439011/shipping-status",  # Valid ObjectId format but non-existent
            404,  # Order not found
            data={
                "status": "in_transit"
            },
            cookies=self.brand_cookies
        )
        
        # Test get order detail without valid order (should fail)
        success, response = self.run_test(
            "Get Order Detail (Invalid Order)",
            "GET",
            "api/orders/507f1f77bcf86cd799439011",  # Valid ObjectId format but non-existent
            404,  # Order not found
            cookies=self.buyer_cookies
        )

    def test_orders_endpoints(self):
        """Test order-related endpoints"""
        print("\n=== TESTING ORDERS ENDPOINTS ===")
        
        # Test my orders (buyer)
        if self.buyer_cookies:
            success, response = self.run_test(
                "Get My Orders (Buyer)",
                "GET",
                "api/orders/my-orders",
                200,
                cookies=self.buyer_cookies
            )
            
            if success and isinstance(response, list):
                print(f"✅ Buyer orders: {len(response)} orders")
        
        # Test brand orders
        if self.brand_cookies:
            success, response = self.run_test(
                "Get Brand Orders",
                "GET",
                "api/orders/brand-orders",
                200,
                cookies=self.brand_cookies
            )
            
            if success and isinstance(response, list):
                print(f"✅ Brand orders: {len(response)} orders")

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n=== CLEANING UP TEST DATA ===")
        
        if self.test_product_id and self.brand_cookies:
            success, response = self.run_test(
                "Delete Test Product",
                "DELETE",
                f"api/products/{self.test_product_id}",
                200,
                cookies=self.brand_cookies
            )
            if success:
                print("✅ Test product cleaned up")

    def run_all_tests(self):
        """Run all tests for reviews and shipping features"""
        print("🚀 Starting Reviews & Shipping Features Tests")
        print(f"🌐 Testing against: {self.base_url}")
        
        # Setup authentication
        self.setup_auth()
        
        # Test new features
        self.test_shipping_couriers()
        self.test_product_with_shipping_cost()
        self.test_reviews_endpoints()
        self.test_order_shipping_flow()
        self.test_orders_endpoints()
        
        # Cleanup
        self.cleanup_test_data()
        
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
    tester = ReviewsShippingTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())