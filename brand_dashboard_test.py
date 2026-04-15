import requests
import sys

def test_brand_dashboard_access():
    """Test the specific brand dashboard access issue that was fixed"""
    base_url = "https://uk-streetwear-hub.preview.emergentagent.com"
    
    print("🔍 Testing Brand Dashboard Access Fix...")
    
    # Create session to maintain cookies
    session = requests.Session()
    
    # 1. Login as demo brand
    print("\n1. Logging in as demo brand...")
    login_response = session.post(
        f"{base_url}/api/auth/login",
        json={
            "email": "demo@threadandbone.uk",
            "password": "Demo123!"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
        return False
    
    print("✅ Brand login successful")
    
    # 2. Test /api/brands/my-application endpoint
    print("\n2. Testing brand application/profile access...")
    app_response = session.get(f"{base_url}/api/brands/my-application")
    
    if app_response.status_code != 200:
        print(f"❌ Brand application access failed: {app_response.status_code} - {app_response.text}")
        return False
    
    app_data = app_response.json()
    print("✅ Brand application endpoint accessible")
    
    # 3. Check if brand profile exists
    if not app_data or not app_data.get('brand_profile'):
        print("❌ No brand profile found in response")
        print(f"Response: {app_data}")
        return False
    
    brand_profile = app_data['brand_profile']
    print(f"✅ Brand profile found: {brand_profile.get('brand_name')}")
    
    # 4. Test getting brand products
    brand_id = brand_profile.get('id')
    if brand_id:
        print(f"\n3. Testing products for brand {brand_id}...")
        products_response = session.get(f"{base_url}/api/products?brand_id={brand_id}")
        
        if products_response.status_code == 200:
            products = products_response.json()
            print(f"✅ Found {len(products)} products for brand")
            
            # Show product details
            for product in products[:3]:  # Show first 3 products
                print(f"  - {product.get('name')} (£{product.get('price')})")
        else:
            print(f"❌ Products fetch failed: {products_response.status_code}")
    
    print("\n🎉 Brand dashboard access test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_brand_dashboard_access()
    sys.exit(0 if success else 1)