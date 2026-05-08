import logging
import os
import threading
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

class BrowserManager:
    _instance = None
    _browser = None
    _playwright = None
    _lock = threading.Lock()
    _idle_timer = None
    _idle_timeout = int(os.getenv("SCREENSHOT_IDLE_TIMEOUT", 60))

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserManager, cls).__new__(cls)
        return cls._instance

    def get_browser(self):
        with self._lock:
            # Cancel any pending idle shutdown
            if self._idle_timer:
                self._idle_timer.cancel()
                self._idle_timer = None
            
            if self._browser is None:
                logger.info("Initializing Playwright (Sync)...")
                self._playwright = sync_playwright().start()
                logger.info("Launching Chromium browser (headless)...")
                self._browser = self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-gpu",
                        "--disable-background-networking",
                        "--disable-sync",
                        "--metrics-recording-only",
                        "--disable-default-apps"
                    ]
                )
            return self._browser

    def schedule_idle_shutdown(self):
        """Schedule browser shutdown after inactivity."""
        with self._lock:
            if self._idle_timer:
                self._idle_timer.cancel()
            
            self._idle_timer = threading.Timer(
                self._idle_timeout, 
                self.shutdown
            )
            self._idle_timer.daemon = True
            self._idle_timer.start()
            logger.debug(f"Scheduled browser idle shutdown in {self._idle_timeout}s")

    def shutdown(self):
        """Force close the browser and stop playwright."""
        with self._lock:
            if self._browser:
                logger.info(f"Shutting down browser after {self._idle_timeout}s of inactivity.")
                try:
                    self._browser.close()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
                self._browser = None
            
            if self._playwright:
                try:
                    self._playwright.stop()
                except Exception as e:
                    logger.error(f"Error stopping playwright: {e}")
                self._playwright = None
            
            self._idle_timer = None

browser_manager = BrowserManager()
