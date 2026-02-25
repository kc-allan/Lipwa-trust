import httpx
import json
import random
from faker import Faker
from typing import List, Dict, Optional

BASE_URL = "http://127.0.0.1:8000"
fake = Faker()

# --- Utility Functions ---

def print_response(title: str, response: httpx.Response):
    print(f"--- {title} ---")
    print(f"Status Code: {response.status_code}")
    try:
        print("Response JSON:", json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print("Response Text:", response.text)

def safe_api_call(func_name: str, func):
    """Wrapper to safely execute API calls and continue on error"""
    try:
        return func()
    except httpx.HTTPStatusError as e:
        print(f"⚠️  {func_name} failed with status {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"⚠️  {func_name} failed with error: {str(e)}")
        return None

def register_user(client: httpx.Client, email: str, password: str, is_merchant: bool = False, is_supplier: bool = False):
    print(f"Registering user: {email} (merchant: {is_merchant}, supplier: {is_supplier})")
    response = client.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password, "is_merchant": is_merchant, "is_supplier": is_supplier}
    )
    print_response("Register User", response)
    if response.status_code >= 400:
        return None
    return response.json()

def login_user(client: httpx.Client, email: str, password: str):
    print(f"Logging in user: {email}")
    response = client.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": password}
    )
    print_response("Login User", response)
    if response.status_code >= 400:
        return None
    
    # Store the access token from the cookie
    if 'access_token' in response.cookies:
        client.cookies.set('access_token', response.cookies['access_token'])
    return response.json()

def generate_merchant_data():
    return {
        "name": fake.company(),
        "business_type": random.choice(["Kibanda", "Duka", "Wholesaler", "Restaurant"]),
        "contact_person": fake.name(),
        "phone_number": fake.phone_number(),
        "email": fake.email(),
        "avg_daily_sales": round(random.uniform(500, 5000), 2),
        "consistency": round(random.uniform(0.4, 0.95), 2),
        "days_active": random.randint(30, 365)
    }

def onboard_merchant(client: httpx.Client, merchant_data: Dict):
    print("Onboarding merchant")
    response = client.post(
        f"{BASE_URL}/merchants/onboard",
        json=merchant_data
    )
    print_response("Onboard Merchant", response)
    if response.status_code >= 400:
        return None
    return response.json()

def generate_supplier_data():
    return {
        "name": fake.company() + " Supplies",
        "contact_person": fake.name(),
        "phone_number": fake.phone_number(),
        "email": fake.email(),
        "product_category": random.choice(["Wholesale Groceries", "Electronics", "Textiles", "Beverages", "Hardware", "Pharmaceuticals"])
    }

def onboard_supplier(client: httpx.Client, supplier_data: Dict):
    print("Onboarding supplier")
    response = client.post(
        f"{BASE_URL}/suppliers/onboard",
        json=supplier_data
    )
    print_response("Onboard Supplier", response)
    if response.status_code >= 400:
        return None
    return response.json()

def get_merchant_score(client: httpx.Client):
    print("Getting merchant's score")
    response = client.get(f"{BASE_URL}/merchant/me/score")
    print_response("Get Merchant Score", response)
    if response.status_code >= 400:
        return None
    return response.json()

def get_merchant_dashboard(client: httpx.Client):
    print("Getting merchant's dashboard")
    response = client.get(f"{BASE_URL}/merchant/me/dashboard")
    print_response("Get Merchant Dashboard", response)
    if response.status_code >= 400:
        return None
    return response.json()

def simulate_daily_sales(client: httpx.Client):
    print("Simulating daily sales for merchant")
    response = client.post(f"{BASE_URL}/merchant/me/simulate_daily_sales")
    print_response("Simulate Daily Sales", response)
    if response.status_code >= 400:
        return None
    return response.json()

def apply_for_credit(client: httpx.Client, amount_requested: float, supplier_db_id: int = None):
    print(f"Applying for credit: {amount_requested}" + (f" with supplier {supplier_db_id}" if supplier_db_id else ""))
    payload = {"amount_requested": amount_requested}
    if supplier_db_id:
        payload["supplier_db_id"] = supplier_db_id
    response = client.post(
        f"{BASE_URL}/credit/apply",
        json=payload
    )
    print_response("Apply for Credit", response)
    if response.status_code >= 400:
        return None
    return response.json()

def record_repayment(client: httpx.Client, contract_id: int, amount: float):
    print(f"Recording repayment for contract {contract_id}, amount {amount}")
    response = client.post(
        f"{BASE_URL}/repayment/settle",
        json={"contract_id": contract_id, "amount": amount}
    )
    print_response("Record Repayment", response)
    if response.status_code >= 400:
        return None
    return response.json()

def get_supplier_me(client: httpx.Client):
    print("Getting supplier's details")
    response = client.get(f"{BASE_URL}/supplier/me")
    print_response("Get Supplier Me", response)
    if response.status_code >= 400:
        return None
    return response.json()

def get_all_suppliers(client: httpx.Client):
    print("Getting all suppliers (as active user)")
    response = client.get(f"{BASE_URL}/suppliers")
    print_response("Get All Suppliers", response)
    if response.status_code >= 400:
        return None
    return response.json()

def get_supplier_contracts(client: httpx.Client):
    print("Getting supplier's contracts")
    response = client.get(f"{BASE_URL}/supplier/me/contracts")
    print_response("Get Supplier Contracts", response)
    if response.status_code >= 400:
        return None
    return response.json()

def get_supplier_active_contracts(client: httpx.Client):
    print("Getting supplier's active contracts")
    response = client.get(f"{BASE_URL}/supplier/me/contracts/active")
    print_response("Get Supplier Active Contracts", response)
    if response.status_code >= 400:
        return None
    return response.json()

# --- Test Orchestration ---
def run_tests():
    print("Starting API Integration Tests...")
    merchant_users_info = []
    supplier_users_info = []

    with httpx.Client(base_url=BASE_URL) as client:
        # Test 1: Register Users
        print("### Phase 1: User Registration ###")
        for i in range(3):
            email = f"merchant{i+1}@example.com"
            password = "password123"
            register_user(client, email, password)
            merchant_users_info.append({"email": email, "password": password, "client": httpx.Client(base_url=BASE_URL)})

            email = f"supplier{i+1}@example.com"
            password = "password123"
            register_user(client, email, password)
            supplier_users_info.append({"email": email, "password": password, "client": httpx.Client(base_url=BASE_URL)})
        
        # Test 2: Login and Onboard Merchants
        print("### Phase 2: Login and Onboard Merchants ###")
        for user_info in merchant_users_info:
            login_user(user_info["client"], user_info["email"], user_info["password"])
            merchant_profile = onboard_merchant(user_info["client"], generate_merchant_data())
            if merchant_profile:
                user_info["merchant_profile"] = merchant_profile # Store profile for later use
            else:
                print(f"⚠️  Failed to onboard merchant {user_info['email']}")

        # Test 3: Login and Onboard Suppliers
        print("### Phase 3: Login and Onboard Suppliers ###")
        for user_info in supplier_users_info:
            login_user(user_info["client"], user_info["email"], user_info["password"])
            supplier_profile = onboard_supplier(user_info["client"], generate_supplier_data())
            if supplier_profile:
                user_info["supplier_profile"] = supplier_profile # Store profile for later use
            else:
                print(f"⚠️  Failed to onboard supplier {user_info['email']}")
        
        # Test 4: Merchant Specific Endpoints
        print("### Phase 4: Merchant Specific Endpoints ###")
        for i, user_info in enumerate(merchant_users_info):
            if "merchant_profile" not in user_info:
                print(f"⚠️  Skipping merchant {i+1} - profile not onboarded")
                continue
            
            print(f"--- Testing Merchant {i+1} ({user_info['email']}) ---")
            
            get_merchant_score(user_info["client"])
            dashboard = get_merchant_dashboard(user_info["client"])
            if not dashboard:
                continue

            # Simulate sales multiple times to see score change
            print("Simulating sales to change trust score...")
            for _ in range(3):
                simulate_daily_sales(user_info["client"])
                
            # Apply for credit
            initial_dashboard = get_merchant_dashboard(user_info["client"])
            if not initial_dashboard:
                continue
                
            credit_limit = initial_dashboard.get('credit_limit', 0)
            
            if credit_limit > 500: # Ensure there's enough credit
                # Pick a random supplier to finance from
                supplier_db_id = None
                if supplier_users_info and i < len(supplier_users_info):
                    supplier_profile = supplier_users_info[i].get("supplier_profile")
                    if supplier_profile:
                        supplier_db_id = supplier_profile.get("id")
                
                contract = apply_for_credit(user_info["client"], credit_limit * 0.5, supplier_db_id=supplier_db_id)
                if contract:
                    # Record repayment
                    record_repayment(user_info["client"], contract['id'], contract['amount_approved'] * 0.25)
                    record_repayment(user_info["client"], contract['id'], contract['amount_approved'] * 0.75) # Fully repay
                else:
                    print(f"⚠️  Skipping repayment - credit application failed")
            else:
                print("Skipping credit application for this merchant due to low credit limit.")

            get_merchant_dashboard(user_info["client"]) # Check updated dashboard

        # Test 5: Supplier Specific Endpoints
        print("### Phase 5: Supplier Specific Endpoints ###")
        for i, user_info in enumerate(supplier_users_info):
            if "supplier_profile" not in user_info:
                print(f"⚠️  Skipping supplier {i+1} - profile not onboarded")
                continue
                
            print(f"--- Testing Supplier {i+1} ({user_info['email']}) ---")
            get_supplier_me(user_info["client"])
            get_supplier_contracts(user_info["client"])  # View all contracts
            get_supplier_active_contracts(user_info["client"])  # View active contracts
        
        # Test 6: General Endpoints (accessible by any active user)
        print("### Phase 6: General Endpoints ###")
        # Use first merchant client to test
        if merchant_users_info:
            print(f"--- Testing GET /suppliers as {merchant_users_info[0]['email']} ---")
            get_all_suppliers(merchant_users_info[0]["client"])

        # Test 7: Unauthorized Access (example)
        print("### Phase 7: Unauthorized Access Tests ###")
        unauth_client = httpx.Client(base_url=BASE_URL)
        print("Attempting to access /merchant/me/dashboard without login:")
        response = unauth_client.get(f"{BASE_URL}/merchant/me/dashboard")
        print_response("Unauthorized Dashboard Access", response)
        if response.status_code != 401:
            print(f"⚠️  Expected 401 but got {response.status_code}")

        if merchant_users_info:
            print("Attempting to access /supplier/me as a merchant:")
            response = merchant_users_info[0]["client"].get(f"{BASE_URL}/supplier/me")
            print_response("Merchant Accessing Supplier Me", response)
            if response.status_code != 403:
                print(f"⚠️  Expected 403 but got {response.status_code}")

    print("\n✅ API Integration Tests Finished.")

if __name__ == "__main__":
    run_tests()
