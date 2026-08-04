import os
from playwright.sync_api import Playwright, sync_playwright, expect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
SHOPIFY_STORE_URL = "https://admin.shopify.com/store/gullahgeecheebiz"
SHOPIFY_DEVELOPMENT_APPS_URL = f"{SHOPIFY_STORE_URL}/settings/apps/development"
APP_NAME = "Gullah Geechee Biz Uploader"

# Scopes to ensure are checked
REQUIRED_SCOPES = {
    "write_products",
    "read_products",
    "write_inventory",
}

# Credentials from .env
SHOPIFY_EMAIL = os.getenv("SHOPIFY_EMAIL")
SHOPIFY_PASSWORD = os.getenv("SHOPIFY_PASSWORD")

if not all([SHOPIFY_EMAIL, SHOPIFY_PASSWORD]):
    print("Error: SHOPIFY_EMAIL and SHOPIFY_PASSWORD must be set in .env")
    exit(1)

def log_progress(message):
    print(f"[PROGRESS] {message}")

def take_screenshot(page, name):
    screenshot_path = f"screenshot_failure_{name}.png"
    page.screenshot(path=screenshot_path)
    print(f"Screenshot taken: {screenshot_path}")

def run(playwright: Playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    try:
        log_progress("Navigating to Shopify admin login...")
        page.goto(f"{SHOPIFY_STORE_URL}/login")
        page.wait_for_selector('input[name="account_email"]')

        log_progress("Entering email...")
        page.fill('input[name="account_email"]', SHOPIFY_EMAIL)
        page.click('button[name="commit"]')

        log_progress("Entering password...")
        # Shopify might redirect to different login flows, handle basic one
        page.wait_for_selector('input[name="password"]')
        page.fill('input[name="password"]', SHOPIFY_PASSWORD)
        page.click('button[name="commit"]')
        
        # Wait for potential 2FA or dashboard
        page.wait_for_url(f"{SHOPIFY_STORE_URL}/", timeout=60000)
        log_progress("Successfully logged into Shopify admin.")

        log_progress("Navigating to Development Apps settings...")
        page.goto(SHOPIFY_DEVELOPMENT_APPS_URL)
        page.wait_for_selector(f'text="{APP_NAME}"')

        log_progress(f"Clicking on app: {APP_NAME}")
        page.click(f'a:has-text("{APP_NAME}")')
        page.wait_for_selector('h1:has-text("App details")')
        log_progress("Opened app details page.")

        log_progress("Navigating to API credentials tab...")
        page.click('a[href*="/api-credentials"]') # Adjust selector if needed
        page.wait_for_selector('h2:has-text("Admin API access tokens")')
        log_progress("On API credentials tab.")

        # Ensure scopes are correct
        log_progress("Checking Admin API scopes...")
        needs_saving = False
        for scope in REQUIRED_SCOPES:
            checkbox_selector = f'input[name="adminApiScopeCheckbox.{scope}"]'
            if not page.is_checked(checkbox_selector):
                log_progress(f"Scope '{scope}' is not checked. Checking it.")
                page.check(checkbox_selector)
                needs_saving = True
            else:
                log_progress(f"Scope '{scope}' is already checked.")

        if needs_saving:
            log_progress("Saving API scopes...")
            page.click('button:has-text("Save")')
            page.wait_for_selector('text="API scopes updated"', timeout=10000)
            log_progress("API scopes saved.")
        else:
            log_progress("All required API scopes are already configured.")

        log_progress("Reinstalling the app to get a fresh token...")
        # Click the "Install app" or "Reinstall app" button.
        # This part might vary. Look for a button that triggers a token refresh.
        # Often it's a 'Reinstall app' or 'Generate token' if it's already installed.
        # We need to find the "Uninstall app" button, then "Install app" to generate a new token.

        # Navigate back to overview to see uninstall button (if needed)
        page.goto(f"{SHOPIFY_DEVELOPMENT_APPS_URL}/{page.url.split('/')[-2]}")
        page.wait_for_selector('h1:has-text("App details")')

        # Find the "Uninstall app" button and click it
        log_progress("Attempting to uninstall the app...")
        try:
            page.click('button:has-text("Uninstall app")')
            page.wait_for_selector('button:has-text("Uninstall app")', state='hidden')
            log_progress("App uninstalled. Now reinstalling...")
            page.click('button:has-text("Install app")')
            page.wait_for_selector('text="App installed"', timeout=30000)
            log_progress("App reinstalled successfully.")
        except Exception:
            # If "Uninstall" not found, assume it's directly reinstallable or token gen.
            log_progress("Uninstall button not found or already uninstalled. Assuming direct token generation via reinstall button if present.")
            try:
                page.click('button:has-text("Install app")') # Try again just in case
                page.wait_for_selector('text="App installed"', timeout=30000)
                log_progress("App reinstalled successfully.")
            except Exception as e:
                log_progress(f"Could not find a clear 'Install app' or 'Reinstall app' button after initial checks. Manual intervention might be needed. Error: {e}")
                take_screenshot(page, "reinstall_failure")
                raise

        log_progress("Navigating back to API credentials to get the new token...")
        page.click('a[href*="/api-credentials"]')
        page.wait_for_selector('h2:has-text("Admin API access tokens")')

        # Extract the new token
        # The selector for the token might vary. Inspect the page to find it.
        # Look for a copy button next to the token, or a span/div containing it.
        token_selector = 'span[aria-label="Admin API access token"]' # Common selector
        new_token = page.locator(token_selector).inner_text().strip()
        
        if not new_token or "shpat_" not in new_token: # Check for common Shopify token prefix
            token_selector_alt = 'input[id="admin_api_access_token"]' # Another common input field
            if page.locator(token_selector_alt).count() > 0:
                new_token = page.locator(token_selector_alt).get_attribute("value")
            else:
                raise ValueError("Could not find the new Shopify API access token.")

        log_progress(f"New Shopify API token extracted: {new_token[:10]}...")

        # Save token to .env
        env_path = ".env"
        with open(env_path, "r") as f:
            lines = f.readlines()

        with open(env_path, "w") as f:
            updated = False
            for line in lines:
                if line.startswith("SHOPIFY_ACCESS_TOKEN="):
                    f.write(f"SHOPIFY_ACCESS_TOKEN={new_token}\n")
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f"SHOPIFY_ACCESS_TOKEN={new_token}\n")
        log_progress("New token saved to .env as SHOPIFY_ACCESS_TOKEN.")
        
        # --- Token Testing (Basic) ---
        log_progress("Attempting a basic API test with the new token...")
        api_test_url = f"https://gullahgeecheebiz.myshopify.com/admin/api/2023-10/products.json"
        
        # Using playwright for a quick test, though usually external http client is better
        # This will make a request from the browser context, which isn't ideal for API testing
        # For a true API test, you'd use requests library outside playwright.
        # This is a placeholder for demonstration purposes.
        
        # Instead of directly hitting the API via browser,
        # we can just confirm the token was copied and stored.
        # A real API test would use the `requests` library outside this Playwright script.
        
        # For the sake of the Playwright script, we'll simulate a network request check,
        # but won't perform an actual external API call with the token here.
        log_progress("To perform a full API test, use a tool like `requests` with the new token.")
        log_progress("Ensure your external API calls are now using this updated SHOPIFY_ACCESS_TOKEN.")

    except Exception as e:
        log_progress(f"An error occurred: {e}")
        take_screenshot(page, "error_final")
    finally:
        log_progress("Closing browser.")
        context.close()
        browser.close()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir) # Change to script's directory to ensure .env is found

    with sync_playwright() as playwright:
        run(playwright)