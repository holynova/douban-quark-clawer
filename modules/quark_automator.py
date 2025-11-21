from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from utils.logger import setup_logger

logger = setup_logger()

class QuarkAutomator:
    def __init__(self, driver):
        self.driver = driver

    def login(self):
        """
        Navigates to Quark and waits for user to log in.
        """
        logger.info("Navigating to Quark for login...")
        self.driver.get("https://pan.quark.cn/")
        
        logger.info("Please log in to Quark in the browser window.")
        logger.info("Waiting for login... (Checking for '我的文件' or similar element)")
        
        # Wait until we see an element that indicates login success
        # e.g. user avatar or file list
        try:
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ant-avatar")) # Example selector, might need adjustment
            )
            logger.info("Login detected!")
        except Exception:
            logger.warning("Login timeout or detection failed. Proceeding anyway, but saving might fail.")

    def save_to_drive(self, url):
        """
        Opens a Quark share URL and clicks 'Save to Drive'.
        """
        logger.info(f"Processing URL: {url}")
        
        # Open in new tab
        self.driver.execute_script(f"window.open('{url}', '_blank');")
        
        # Switch to new tab
        self.driver.switch_to.window(self.driver.window_handles[-1])
        
        try:
            # Wait for page load
            time.sleep(3)
            
            # Find "Save to Drive" button
            # Selectors might change, need to be robust
            # Usually text contains "转存" or "保存"
            
            # Try XPath by text
            save_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., '转存') or contains(., '保存')]"))
            )
            save_btn.click()
            logger.info("Clicked 'Save to Drive'.")
            
            # Handle "Select Location" dialog if it appears
            # Usually there's a "Confirm" button in a modal
            try:
                confirm_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'ant-modal')]//button[contains(., '确定') or contains(., '转存')]"))
                )
                confirm_btn.click()
                logger.info("Confirmed save location.")
            except:
                logger.info("No location selection dialog or auto-saved.")
            
            # Wait for success message
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to save {url}: {e}")
            try:
                self.driver.save_screenshot(f"error_save_{int(time.time())}.png")
            except:
                pass
        
        # Close tab
        self.driver.close()
        
        # Switch back to main tab
        self.driver.switch_to.window(self.driver.window_handles[0])
