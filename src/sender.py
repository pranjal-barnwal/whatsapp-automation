"""Selenium-driven WhatsApp Web sender.

Uses a persistent Chrome profile so the QR code is scanned only once. For each
client we open the pre-filled ``web.whatsapp.com/send`` deep link, wait for the
chat to load, detect the "invalid number" dialog, send, and confirm delivery.
"""
from __future__ import annotations

import random
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from . import config
from .message_builder import build_web_send_url


class SendError(Exception):
    """Raised when a message could not be sent to a valid-looking number."""


class InvalidNumberError(SendError):
    """Raised when WhatsApp reports the phone number is not on WhatsApp."""


# XPath fragments for the WhatsApp Web UI. These occasionally change when
# WhatsApp updates its web client; keep them in one place for easy updates.
_XPATH_SEND_BUTTON = "//button[@aria-label='Send' or @data-testid='send']"
_XPATH_MESSAGE_BOX = (
    "//div[@contenteditable='true'][@data-tab='10' or @aria-label]"
    "[@role='textbox']"
)
_XPATH_INVALID_DIALOG = (
    "//*[contains(text(), 'Phone number shared via url is invalid') or "
    "contains(text(), 'phone number shared via url is invalid') or "
    "contains(text(), \"isn't on WhatsApp\") or "
    "contains(text(), 'is not on WhatsApp')]"
)
_XPATH_QR_CANVAS = "//canvas[@aria-label='Scan me!' or @role='img']"
_XPATH_CHAT_READY = "//footer//div[@contenteditable='true']"


class WhatsAppSender:
    """Manages a single Chrome/WhatsApp Web session for a batch of sends."""

    def __init__(
        self,
        profile_dir: Path = config.PROFILE_DIR,
        headless: bool = False,
    ) -> None:
        self.profile_dir = Path(profile_dir)
        self.headless = headless
        self.driver: webdriver.Chrome | None = None

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> None:
        """Launch Chrome and wait until WhatsApp Web is logged in."""
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        options = Options()
        options.add_argument(f"--user-data-dir={self.profile_dir.resolve()}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-notifications")
        options.add_argument("--start-maximized")
        # Reduce noisy automation banners / logging.
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,900")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)

        self._wait_for_login()

    def _wait_for_login(self) -> None:
        """Open WhatsApp Web and block until the user is logged in."""
        assert self.driver is not None
        self.driver.get("https://web.whatsapp.com/")

        print("Opening WhatsApp Web...")
        deadline = time.time() + 180  # allow up to 3 minutes to scan the QR
        announced_qr = False
        while time.time() < deadline:
            if self._is_logged_in():
                print("WhatsApp Web is ready.")
                return
            if not announced_qr and self._element_present(_XPATH_QR_CANVAS):
                print("Scan the QR code in the browser to log in...")
                announced_qr = True
            time.sleep(2)

        raise SendError("Timed out waiting for WhatsApp Web login.")

    def _is_logged_in(self) -> bool:
        """Heuristic: the chat/search pane is present once logged in."""
        assert self.driver is not None
        selectors = [
            "//div[@id='side']",
            "//div[@contenteditable='true'][@data-tab='3']",
        ]
        return any(self._element_present(sel) for sel in selectors)

    def _element_present(self, xpath: str) -> bool:
        assert self.driver is not None
        try:
            self.driver.find_element(By.XPATH, xpath)
            return True
        except (NoSuchElementException, WebDriverException):
            return False

    def stop(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            finally:
                self.driver = None

    def __enter__(self) -> "WhatsAppSender":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    # -- sending --------------------------------------------------------------
    def send(self, phone: str, message: str) -> None:
        """Send ``message`` to ``phone`` (country-code-prefixed digits).

        Raises ``InvalidNumberError`` if the number is not on WhatsApp, or
        ``SendError`` for any other failure.
        """
        if self.driver is None:
            raise SendError("Sender not started; call start() first.")

        url = build_web_send_url(phone, message)
        self.driver.get(url)

        wait = WebDriverWait(self.driver, config.ELEMENT_TIMEOUT)

        # The chat either loads (message box appears) or the invalid dialog shows.
        try:
            wait.until(
                lambda d: self._element_present(_XPATH_SEND_BUTTON)
                or self._element_present(_XPATH_CHAT_READY)
                or self._element_present(_XPATH_INVALID_DIALOG)
            )
        except TimeoutException as exc:
            raise SendError("Chat did not load in time.") from exc

        if self._element_present(_XPATH_INVALID_DIALOG):
            self._dismiss_invalid_dialog()
            raise InvalidNumberError("Number is not on WhatsApp or is invalid.")

        # Click the send button; fall back to pressing Enter in the message box.
        if not self._click_send(wait):
            self._press_enter_fallback()

        self._wait_until_sent()

    def _click_send(self, wait: WebDriverWait) -> bool:
        assert self.driver is not None
        try:
            button = wait.until(
                EC.element_to_be_clickable((By.XPATH, _XPATH_SEND_BUTTON))
            )
            button.click()
            return True
        except (TimeoutException, WebDriverException):
            return False

    def _press_enter_fallback(self) -> None:
        assert self.driver is not None
        from selenium.webdriver.common.keys import Keys

        try:
            box = self.driver.find_element(By.XPATH, _XPATH_MESSAGE_BOX)
            box.send_keys(Keys.ENTER)
        except (NoSuchElementException, WebDriverException) as exc:
            raise SendError("Could not locate the message box to send.") from exc

    def _wait_until_sent(self) -> None:
        """Wait briefly for the pending clock icon to clear (message left device)."""
        assert self.driver is not None
        pending_xpath = "//span[@data-icon='msg-time']"
        deadline = time.time() + 20
        # First give the message a moment to appear in the thread.
        time.sleep(1.5)
        while time.time() < deadline:
            if not self._element_present(pending_xpath):
                return
            time.sleep(1)
        # Not fatal: message may still deliver; caller logs as sent optimistically.

    def _dismiss_invalid_dialog(self) -> None:
        assert self.driver is not None
        ok_xpath = "//div[@role='button']//div[text()='OK'] | //button[text()='OK']"
        try:
            self.driver.find_element(By.XPATH, ok_xpath).click()
        except (NoSuchElementException, WebDriverException):
            pass


def human_delay(
    min_seconds: float = config.MIN_DELAY_SECONDS,
    max_seconds: float = config.MAX_DELAY_SECONDS,
) -> float:
    """Sleep a randomised amount between messages; returns the seconds waited."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay
