#!/usr/bin/env python3
"""
API SETUP BOT — Playwright-based credential provisioning tool.

Automates app registration, API key generation, OAuth flows, and credential
validation across distribution platforms for Gullah Geechee Biz.

Author: Publishing Automation Engineer
Target: /Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/api-setup-bot.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import re
import secrets
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: requests. Run `pip install requests`.")

try:
    from dotenv import load_dotenv, set_key, dotenv_values
except ImportError:
    sys.exit("Missing dependency: python-dotenv. Run `pip install python-dotenv`.")

try:
    from playwright.sync_api import (
        sync_playwright,
        Browser,
        BrowserContext,
        Page,
        Playwright,
        TimeoutError as PWTimeout,
    )
except ImportError:
    sys.exit("Missing dependency: playwright. Run `pip install playwright && playwright install chromium`.")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent  # ggb-engine
PROJECT_ROOT = REPO_ROOT.parent  # gullahgeecheebiz-site
ENV_PATH = PROJECT_ROOT / ".env"
STATE_PATH = HERE / "api_setup_state.json"
LOG_PATH = HERE / "api_setup_bot.log"
SCREENSHOTS_DIR = HERE / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _configure_logging(verbose: bool) -> logging.Logger:
    logger = logging.getLogger("api_setup_bot")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"
    )

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


log = _configure_logging(False)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class Credential:
    platform: str
    key: str           # .env variable name
    value: str
    kind: str = "token"  # token | key | secret | id | url

    def masked(self) -> str:
        v = self.value
        if len(v) <= 8:
            return "****"
        return f"{v[:4]}...{v[-4:]}"


@dataclass
class PlatformResult:
    platform: str
    status: str = "pending"         # pending | success | failed | skipped | manual
    credentials: List[Credential] = field(default_factory=list)
    api_test_ok: bool = False
    api_test_detail: str = ""
    error: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "status": self.status,
            "credentials": [asdict(c) for c in self.credentials],
            "api_test_ok": self.api_test_ok,
            "api_test_detail": self.api_test_detail,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlatformResult":
        r = cls(platform=d["platform"])
        r.status = d.get("status", "pending")
        r.credentials = [Credential(**c) for c in d.get("credentials", [])]
        r.api_test_ok = d.get("api_test_ok", False)
        r.api_test_detail = d.get("api_test_detail", "")
        r.error = d.get("error", "")
        r.started_at = d.get("started_at")
        r.finished_at = d.get("finished_at")
        return r


# ---------------------------------------------------------------------------
# State persistence (resumability)
# ---------------------------------------------------------------------------
class StateStore:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self.results: Dict[str, PlatformResult] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text())
                for name, body in raw.get("results", {}).items():
                    self.results[name] = PlatformResult.from_dict(body)
                log.info("Loaded state with %d platform(s) from %s",
                         len(self.results), self.path.name)
            except Exception as exc:
                log.warning("Failed to load state (%s); starting fresh.", exc)

    def save(self) -> None:
        payload = {
            "updated_at": dt.datetime.utcnow().isoformat() + "Z",
            "results": {k: v.to_dict() for k, v in self.results.items()},
        }
        self.path.write_text(json.dumps(payload, indent=2))

    def get(self, platform: str) -> PlatformResult:
        if platform not in self.results:
            self.results[platform] = PlatformResult(platform=platform)
        return self.results[platform]

    def reset(self, platform: str) -> None:
        self.results[platform] = PlatformResult(platform=platform)


# ---------------------------------------------------------------------------
# .env manager
# ---------------------------------------------------------------------------
class EnvManager:
    def __init__(self, path: Path = ENV_PATH):
        self.path = path
        if not self.path.exists():
            self.path.write_text(
                "# Generated by api-setup-bot.py\n"
                f"# Created: {dt.datetime.utcnow().isoformat()}Z\n\n"
            )
        load_dotenv(self.path, override=True)

    def set(self, key: str, value: str) -> None:
        """Write a key to .env (idempotent) and update os.environ."""
        set_key(str(self.path), key, value)
        os.environ[key] = value

    def set_many(self, creds: List[Credential]) -> None:
        for c in creds:
            self.set(c.key, c.value)

    def get(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def values(self) -> Dict[str, str]:
        return dotenv_values(self.path)


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------
class BrowserSession:
    """Context manager around a Playwright browser with persistent storage."""

    def __init__(self, headless: bool = False, slow_mo: int = 50):
        self.headless = headless
        self.slow_mo = slow_mo
        self.pw: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.storage_dir = HERE / "browser_state"
        self.storage_dir.mkdir(exist_ok=True)
        self.storage_file = self.storage_dir / "auth_state.json"

    def __enter__(self) -> "BrowserSession":
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        ctx_args = {
            "viewport": {"width": 1400, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        if self.storage_file.exists():
            ctx_args["storage_state"] = str(self.storage_file)
        self.context = self.browser.new_context(**ctx_args)
        self.context.set_default_timeout(45_000)
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self.context:
                self.context.storage_state(path=str(self.storage_file))
        except Exception as e:
            log.debug("Could not persist auth state: %s", e)
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()

    def screenshot(self, name: str) -> Path:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = SCREENSHOTS_DIR / f"{ts}_{name}.png"
        self.page.screenshot(path=str(path), full_page=False)
        log.debug("Screenshot saved: %s", path)
        return path


def human_pause(message: str, timeout_seconds: int = 0) -> None:
    """Pause for human intervention (CAPTCHA / 2FA / email verification)."""
    print()
    print("=" * 70)
    print(f"  HUMAN ACTION REQUIRED: {message}")
    if timeout_seconds:
        print(f"  Will auto-continue in {timeout_seconds}s if no input.")
    print("  Press ENTER when done, or type 'skip' to abort this platform.")
    print("=" * 70)
    try:
        if timeout_seconds:
            import select
            ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
            if ready:
                line = sys.stdin.readline().strip()
            else:
                line = ""
        else:
            line = input("> ").strip()
    except EOFError:
        line = ""
    if line.lower() == "skip":
        raise RuntimeError("User skipped this platform.")


def prompt_secret(prompt: str, env_fallback: str = "") -> str:
    """Ask user for a secret with an optional env-var fallback."""
    if env_fallback and os.environ.get(env_fallback):
        print(f"  Using existing {env_fallback} from environment.")
        return os.environ[env_fallback]
    try:
        import getpass
        return getpass.getpass(f"{prompt}: ").strip()
    except Exception:
        return input(f"{prompt}: ").strip()


# ---------------------------------------------------------------------------
# Base platform handler
# ---------------------------------------------------------------------------
class PlatformHandler:
    """Abstract-ish base class. Each platform implements setup() + api_test()."""

    name: str = "base"
    display_name: str = "Base"
    developer_url: str = ""
    env_keys: List[str] = []          # expected env vars after success
    login_required: bool = True
    captcha_likely: bool = False
    twofa_likely: bool = False

    def __init__(self, session: BrowserSession, env: EnvManager, state: StateStore,
                 interactive: bool = True):
        self.session = session
        self.env = env
        self.state = state
        self.interactive = interactive
        self.result = self.state.get(self.name)

    # -- lifecycle --
    def run(self, force: bool = False) -> PlatformResult:
        if self.result.status == "success" and not force:
            log.info("[%s] Already succeeded. Use --force to redo.", self.name)
            return self.result

        self.result.status = "pending"
        self.result.started_at = dt.datetime.utcnow().isoformat() + "Z"
        self.result.error = ""
        self.state.save()

        try:
            creds = self.setup()
            self.result.credentials = creds
            if creds:
                self.env.set_many(creds)
                log.info("[%s] Saved %d credential(s) to %s",
                         self.name, len(creds), self.env.path.name)

            ok, detail = self.api_test()
            self.result.api_test_ok = ok
            self.result.api_test_detail = detail
            self.result.status = "success" if ok else "failed"
            if not ok:
                self.result.error = f"API test failed: {detail}"

        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log.exception("[%s] Setup failed.", self.name)
            self.result.status = "failed"
            self.result.error = str(exc)
            try:
                self.session.screenshot(f"FAIL_{self.name}")
            except Exception:
                pass

        self.result.finished_at = dt.datetime.utcnow().isoformat() + "Z"
        self.state.save()
        return self.result

    # -- to be overridden --
    def setup(self) -> List[Credential]:
        raise NotImplementedError

    def api_test(self) -> Tuple[bool, str]:
        return True, "no api test implemented"

    # -- helpers --
    def _need_login(self, page: Page, login_url: str) -> None:
        """Navigate and give the human a chance to log in / pass CAPTCHA / 2FA."""
        page.goto(login_url, wait_until="domcontentloaded")
        if self.interactive:
            human_pause(
                f"Log in to {self.display_name} and complete any CAPTCHA/2FA. "
                f"Once on the dashboard, press ENTER."
            )

    def _wait_for_url_contains(self, page: Page, substr: str, timeout_ms: int = 120_000):
        page.wait_for_url(f"**{substr}**", timeout=timeout_ms)


# ---------------------------------------------------------------------------
# PINTEREST
# ---------------------------------------------------------------------------
class PinterestHandler(PlatformHandler):
    name = "pinterest"
    display_name = "Pinterest"
    developer_url = "https://developers.pinterest.com/"
    env_keys = ["PINTEREST_APP_ID", "PINTEREST_APP_SECRET", "PINTEREST_ACCESS_TOKEN"]
    login_required = True
    captcha_likely = False
    twofa_likely = True

    APP_NAME = "Gullah Geechee Biz Publisher"
    APP_DESC = "Automated book distribution and pin publishing for Gullah Geechee Biz."

    def setup(self) -> List[Credential]:
        page = self.session.page
        self._need_login(page, "https://developers.pinterest.com/apps/")

        # Try to find or create the app
        page.goto("https://developers.pinterest.com/apps/", wait_until="domcontentloaded")
        time.sleep(2)

        # Look for existing app by name
        existing = page.query_selector(f"text={self.APP_NAME}")
        if existing:
            log.info("[%s] Found existing app; opening it.", self.name)
            existing.click()
        else:
            log.info("[%s] Creating new app.", self.name)
            # Click "Create app" — Pinterest rotates selectors, so be defensive
            for candidate in ["text=Create app", "text=Create new app", "button:has-text('Create')"]:
                try:
                    btn = page.wait_for_selector(candidate, timeout=5000)
                    if btn:
                        btn.click()
                        break
                except PWTimeout:
                    continue
            else:
                self.session.screenshot("pinterest_create_app_not_found")
                if self.interactive:
                    human_pause("Could not find 'Create app' button. Create it manually, then press ENTER.")

            # Fill form
            self._fill_textbox(page, "Name", self.APP_NAME)
            self._fill_textbox(page, "Description", self.APP_DESC)
            # Accept / submit
            for candidate in ["text=Submit", "button:has-text('Submit')", "button:has-text('Create')"]:
                try:
                    btn = page.wait_for_selector(candidate, timeout=4000)
                    if btn:
                        btn.click()
                        break
                except PWTimeout:
                    continue

        time.sleep(3)
        self.session.screenshot("pinterest_app_page")

        # Extract credentials from the app page
        app_id = self._extract_labeled_value(page, ["App ID", "Client ID", "ID"])
        app_secret = self._extract_labeled_value(page, ["App secret", "Client secret", "Secret"])

        creds: List[Credential] = []
        if app_id:
            creds.append(Credential(self.name, "PINTEREST_APP_ID", app_id, "id"))
        if app_secret:
            creds.append(Credential(self.name, "PINTEREST_APP_SECRET", app_secret, "secret"))

        # Generate access token (OAuth)
        token = self._generate_token(page)
        if token:
            creds.append(Credential(self.name, "PINTEREST_ACCESS_TOKEN", token, "token"))

        if not creds:
            raise RuntimeError(
                "Could not extract any Pinterest credentials. "
                "See screenshots/ and complete manually."
            )
        return creds

    def _fill_textbox(self, page: Page, label_substr: str, value: str) -> None:
        try:
            lbl = page.locator(f"label:has-text('{label_substr}')").first
            target = lbl.locator("xpath=ancestor::*[.//input or .//textarea][1]//input | "
                                 "ancestor::*[.//input or .//textarea][1]//textarea").first
            target.fill(value)
        except Exception:
            try:
                page.locator(f"input[placeholder*='{label_substr}'], "
                             f"textarea[placeholder*='{label_substr}']").first.fill(value)
            except Exception as e:
                log.debug("[%s] Could not fill '%s': %s", self.name, label_substr, e)

    def _extract_labeled_value(self, page: Page, labels: List[str]) -> Optional[str]:
        for label in labels:
            try:
                # Look for text then next sibling or adjacent element
                el = page.locator(f"text='{label}'").first
                parent = el.locator("xpath=..")
                text = parent.inner_text()
                # Find token-like substrings
                for chunk in re.split(r"\s+", text):
                    chunk = chunk.strip(" ,:")
                    if len(chunk) >= 8 and re.match(r"^[A-Za-z0-9_\-]+$", chunk) and chunk != label:
                        return chunk
            except Exception:
                continue
        # Fallback: ask the user
        if self.interactive:
            return prompt_secret(
                f"Could not auto-extract {'/'.join(labels)}. Paste value (or blank to skip)",
                env_fallback="",
            ) or None
        return None

    def _generate_token(self, page: Page) -> Optional[str]:
        # Try to click "Generate" on the token section
        for candidate in ["text=Generate", "button:has-text('Generate')",
                          "text=Generate access token", "button:has-text('Token')"]:
            try:
                btn = page.locator(candidate).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    time.sleep(2)
                    self.session.screenshot("pinterest_token_generated")
                    # Try to read the token from a modal / input
                    for sel in ["input[readonly]", "code", "pre", ".token-value", "[data-testid='token']"]:
                        try:
                            node = page.locator(sel).first
                            val = (node.input_value()
                                   if node.evaluate("el => el.tagName === 'INPUT'")
                                   else node.inner_text())
                            val = val.strip()
                            if len(val) >= 16 and re.match(r"^[A-Za-z0-9_\-\.]+$", val):
                                return val
                        except Exception:
                            continue
                    break
            except Exception:
                continue
        if self.interactive:
            return prompt_secret(
                "Paste Pinterest access token (from developer console)",
                env_fallback="PINTEREST_ACCESS_TOKEN",
            ) or None
        return None

    def api_test(self) -> Tuple[bool, str]:
        token = self.env.get("PINTEREST_ACCESS_TOKEN")
        if not token:
            return False, "no access token available"
        try:
            r = requests.get(
                "https://api.pinterest.com/v5/user_account",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                return True, f"ok username={data.get('username')}"
            return False, f"HTTP {r.status_code}: {r.text[:120]}"
        except Exception as e:
            return False, f"request error: {e}"


# ---------------------------------------------------------------------------
# SHOPIFY
# ---------------------------------------------------------------------------
class ShopifyHandler(PlatformHandler):
    name = "shopify"
    display_name = "Shopify"
    developer_url = "https://partners.shopify.com/"
    env_keys = [
        "SHOPIFY_SHOP_DOMAIN",
        "SHOPIFY_API_KEY",
        "SHOPIFY_API_SECRET",
        "SHOPIFY_ACCESS_TOKEN",
    ]
    login_required = True
    twofa_likely = True

    APP_NAME = "Gullah Geechee Biz Books"
    SCOPES = "read_products,write_products,read_orders,write_orders,read_inventory,write_inventory"

    def setup(self) -> List[Credential]:
        page = self.session.page
        self._need_login(page, "https://partners.shopify.com/")

        shop_domain = self.env.get("SHOPIFY_SHOP_DOMAIN")
        if not shop_domain and self.interactive:
            shop_domain = input("  Shopify shop domain (e.g. gullahgeecheebiz.myshopify.com): ").strip()
        if not shop_domain:
            raise RuntimeError("SHOPIFY_SHOP_DOMAIN is required.")

        # Build a Custom App via admin API (faster + more reliable than UI)
        # First: ask user for existing API key/secret if they already have a custom app
        api_key = prompt_secret(
            "  Shopify Custom App API Key (leave blank to create via admin UI)",
            env_fallback="SHOPIFY_API_KEY",
        )
        api_secret = prompt_secret(
            "  Shopify Custom App API Secret (leave blank if unknown)",
            env_fallback="SHOPIFY_API_SECRET",
        )
        admin_token = prompt_secret(
            "  Shopify Admin API access token (Custom App token)",
            env_fallback="SHOPIFY_ACCESS_TOKEN",
        )

        # If no token yet, walk user through Custom App creation
        if not admin_token:
            admin_url = f"https://{shop_domain}/admin/settings/apps/development"
            page.goto(admin_url, wait_until="domcontentloaded")
            if self.interactive:
                human_pause(
                    "Enable custom app development if prompted. "
                    "Then create a Custom App named '" + self.APP_NAME + "' "
                    "with the required scopes. Paste the Admin API access token below."
                )
            admin_token = prompt_secret("  Paste Custom App Admin API access token",
                                        env_fallback="SHOPIFY_ACCESS_TOKEN")

        # Grab api_key/secret from the app page if still missing
        if not api_key or not api_secret:
            try:
                page.goto(f"https://{shop_domain}/admin/settings/apps/development",
                          wait_until="domcontentloaded")
                time.sleep(2)
                self.session.screenshot("shopify_apps_page")
            except Exception:
                pass
            api_key = api_key or prompt_secret("  Shopify API Key", env_fallback="SHOPIFY_API_KEY")
            api_secret = api_secret or prompt_secret("  Shopify API Secret", env_fallback="SHOPIFY_API_SECRET")

        creds = [
            Credential(self.name, "SHOPIFY_SHOP_DOMAIN", shop_domain, "url"),
        ]
        if api_key:
            creds.append(Credential(self.name, "SHOPIFY_API_KEY", api_key, "key"))
        if api_secret:
            creds.append(Credential(self.name, "SHOPIFY_API_SECRET", api_secret, "secret"))
        if admin_token:
            creds.append(Credential(self.name, "SHOPIFY_ACCESS_TOKEN", admin_token, "token"))
        return creds

    def api_test(self) -> Tuple[bool, str]:
        shop = self.env.get("SHOPIFY_SHOP_DOMAIN")
        token = self.env.get("SHOPIFY_ACCESS_TOKEN")
        if not (shop and token):
            return False, "missing SHOPIFY_SHOP_DOMAIN or SHOPIFY_ACCESS_TOKEN"
        url = f"https://{shop}/admin/api/2024-04/shop.json"
        try:
            r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=15)
            if r.status_code == 200:
                data = r.json().get("shop", {})
                return True, f"ok shop={data.get('name')}"
            return False, f"HTTP {r.status_code}: {r.text[:120]}"
        except Exception as e:
            return False, f"request error: {e}"


# ---------------------------------------------------------------------------
# ETSY
# ---------------------------------------------------------------------------
class EtsyHandler(PlatformHandler):
    name = "etsy"
    display_name = "Etsy"
    developer_url = "https://www.etsy.com/developers"
    env_keys = ["ETSY_API_KEY", "ETSY_KEYSTRING", "ETSY_SHARED_SECRET", "ETSY_OAUTH_TOKEN"]
    login_required = True
    captcha_likely = True

    APP_NAME = "GullahGeecheeBizBooks"

    def setup(self) -> List[Credential]:
        page = self.session.page
        self._need_login(page, "https://www.etsy.com/developers")

        page.goto("https://www.etsy.com/developers", wait_until="domcontentloaded")
        time.sleep(2)

        # Try to create a new app
        for candidate in ["text=Create new app", "text=Create App", "text=New App"]:
            try:
                btn = page.locator(candidate).first
                if btn.is_visible(timeout=2500):
                    btn.click()
                    time.sleep(1)
                    break
            except Exception:
                continue

        # Fill app name/description
        try:
            name_input = page.locator("input[name='name'], input[id*='name']").first
            name_input.fill(self.APP_NAME)
        except Exception:
            pass
        try:
            desc_input = page.locator("textarea[name='description']").first
            desc_input.fill("Book distribution integration for Gullah Geechee Biz.")
        except Exception:
            pass

        # Submit
        for candidate in ["button:has-text('Create')", "button:has-text('Submit')",
                          "button:has-text('Save')"]:
            try:
                btn = page.locator(candidate).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    time.sleep(2)
                    break
            except Exception:
                continue

        self.session.screenshot("etsy_app_page")

        keystring = self._grab_visible_text_match(page, r"^[A-Za-z0-9]{20,40}$")
        shared_secret = self._grab_visible_text_match(page, r"^[A-Za-z0-9]{24,64}$",
                                                     exclude=keystring)

        if self.interactive and (not keystring or not shared_secret):
            human_pause(
                "Copy your Etsy Keystring and Shared Secret from the app page, "
                "then press ENTER."
            )
            keystring = keystring or prompt_secret("  Etsy Keystring", "ETSY_KEYSTRING")
            shared_secret = shared_secret or prompt_secret("  Etsy Shared Secret",
                                                           "ETSY_SHARED_SECRET")

        creds: List[Credential] = []
        if keystring:
            creds.append(Credential(self.name, "ETSY_KEYSTRING", keystring, "key"))
            creds.append(Credential(self.name, "ETSY_API_KEY", keystring, "key"))
        if shared_secret:
            creds.append(Credential(self.name, "ETSY_SHARED_SECRET", shared_secret, "secret"))

        # OAuth PKCE is required for Etsy v3 — we generate a token through the
        # browser flow. We'll open the auth URL and capture the code.
        oauth_token = self._etsy_oauth(keystring, shared_secret)
        if oauth_token:
            creds.append(Credential(self.name, "ETSY_OAUTH_TOKEN", oauth_token, "token"))

        if not creds:
            raise RuntimeError("Could not obtain Etsy credentials.")
        return creds

    def _grab_visible_text_match(self, page: Page, pattern: str,
                                 exclude: Optional[str] = None) -> Optional[str]:
        try:
            all_text = page.locator("body").inner_text()
        except Exception:
            return None
        for chunk in re.split(r"\s+", all_text):
            chunk = chunk.strip(" ,:;")
            if re.match(pattern, chunk) and chunk != exclude:
                return chunk
        return None

    def _etsy_oauth(self, keystring: Optional[str], shared_secret: Optional[str]) -> Optional[str]:
        if not keystring:
            return None
        import hashlib, base64
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        redirect_uri = "https://localhost"
        scopes = "listings_w listings_r shops_r"
        url = (
            "https://www.etsy.com/oauth/connect"
            f"?response_type=code&client_id={keystring}"
            f"&redirect_uri={redirect_uri}&scope={scopes}"
            f"&state={state}&code_challenge={challenge}"
            f"&code_challenge_method=S256"
        )
        page = self.session.page
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        except Exception:
            return None

        if self.interactive:
            human_pause("Authorize the Etsy app. After redirect to localhost, paste the code below.")

        code = prompt_secret("  Etsy OAuth code (from redirect URL ?code=...)")
        if not code:
            return None

        # Exchange code for token
        try:
            r = requests.post(
                "https://api.etsy.com/v3/public/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": keystring,
                    "redirect_uri": redirect_uri,
                    "code": code,
                    "code_verifier": verifier,
                },
                timeout=15,
            )
            if r.status_code == 200:
                return r.json().get("access_token")
            log.warning("[%s] OAuth token exchange failed: %s", self.name, r.text[:160])
        except Exception as e:
            log.warning("[%s] OAuth token exchange error: %s", self.name, e)
        return None

    def api_test(self) -> Tuple[bool, str]:
        keystring = self.env.get("ETSY_KEYSTRING") or self.env.get("ETSY_API_KEY")
        token = self.env.get("ETSY_OAUTH_TOKEN")
        if not keystring:
            return False, "missing ETSY_KEYSTRING"
        headers = {"x-api-key": keystring}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            r = requests.get(
                "https://openapi.etsy.com/v3/application/shop",
                headers=headers, timeout=15,
            )
            if r.status_code == 200:
                return True, "ok shop listing returned"
            # 403 can be expected if the shop isn't linked yet; still counts as
            # 'the key works' at the authentication layer
            if r.status_code == 403 and token:
                return True, f"auth ok (no linked shop yet): {r.text[:80]}"
            return False, f"HTTP {r.status_code}: {r.text[:120]}"
        except Exception as e:
            return False, f"request error: {e}"


# ---------------------------------------------------------------------------
# DRAFT2DIGITAL
# ---------------------------------------------------------------------------
class Draft2DigitalHandler(PlatformHandler):
    name = "draft2digital"
    display_name = "Draft2Digital"
    developer_url = "https://www.draft2digital.com/"
    env_keys = ["D2