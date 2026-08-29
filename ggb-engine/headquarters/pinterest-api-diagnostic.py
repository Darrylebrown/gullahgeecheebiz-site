import requests
import json
import _env_creds

# Configuration
PINTEREST_APP_ID = _env_creds.require("PINTEREST_APP_ID")
PINTEREST_ACCESS_TOKEN = _env_creds.require("PINTEREST_ACCESS_TOKEN")
ENDPOINTS = {
    "Production": "https://api.pinterest.com/v5/user_account",
    "Sandbox": "https://api-sandbox.pinterest.com/v5/user_account"
}

def make_request(url, headers=None, params=None):
    """Helper function to make an HTTP GET request and return the response."""
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP Error: {e.response.status_code} - {e.response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request Exception: {e}"}

def run_tests():
    """Runs various tests against Pinterest API endpoints."""
    print("--- Pinterest API Access Diagnostic ---")

    test_scenarios = [
        {"desc": "Prod - Auth Header Only", "headers": {"Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}"}},
        {"desc": "Prod - Auth Header + X-Pinterest-App-Id", "headers": {"Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}", "X-Pinterest-App-Id": PINTEREST_APP_ID}},
        {"desc": "Prod - Auth Header + client_id in params", "headers": {"Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}"}, "params": {"client_id": PINTEREST_APP_ID}},
        {"desc": "Sandbox - Auth Header Only", "headers": {"Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}"}, "endpoint_key": "Sandbox"},
        {"desc": "Sandbox - Auth Header + X-Pinterest-App-Id", "headers": {"Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}", "X-Pinterest-App-Id": PINTEREST_APP_ID}, "endpoint_key": "Sandbox"},
        {"desc": "Sandbox - Auth Header + client_id in params", "headers": {"Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}"}, "params": {"client_id": PINTEREST_APP_ID}, "endpoint_key": "Sandbox"},
    ]

    for scenario in test_scenarios:
        desc = scenario["desc"]
        headers = scenario.get("headers")
        params = scenario.get("params")
        endpoint_key = scenario.get("endpoint_key", "Production")
        url = ENDPOINTS[endpoint_key]

        print(f"\n--- Testing Scenario: {desc} ({endpoint_key}) ---")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        print(f"Params: {params}")

        result = make_request(url, headers=headers, params=params)

        print(f"Result: {json.dumps(result, indent=2)}")
        if "error" in result or (isinstance(result, dict) and "code" in result and result.get("code") != 0):
            print("Status: FAILED")
        else:
            print("Status: SUCCESS (unexpected if 'consumer type' error is consistent)")

    print("\n--- Diagnostic Complete ---")
    print("\n--- Suggested fix for 'application consumer type is not supported' ---")
    print("This error often indicates that the application's 'App Type' or 'Use Case' in the Pinterest Developer App Settings is not configured correctly for the desired API access.")
    print("Please go to your Pinterest Developer App Dashboard (for app ID 1597343):")
    print("1. Navigate to 'Settings' for your application.")
    print("2. Look for 'App Type', 'Use Case', or 'Platform' settings.")
    print("3. Ensure it's set to a type that allows read/write access for your intended purpose (e.g., 'Business App', 'Marketing API', 'Partnership').")
    print("4. You may need to request elevated access or specific scopes if your app's default type is too restrictive (e.g., 'Internal Tool' or 'Consumer').")
    print("5. Also, verify that the 'Scopes' granted to your access token include `user_accounts:read` (and any other necessary scopes). If the token was generated with limited scopes, it might need to be regenerated after updating app settings.")
    print("6. If the issue persists, contact Pinterest Developer Support with your App ID and the exact error messages.")

if __name__ == "__main__":
    run_tests()