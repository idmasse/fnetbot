import os
import time
import logging
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5 # seconds

def fnet_login(driver, username, password):
    # selenium syntax shortcuts
    short_wait = WebDriverWait(driver, 10)
    long_wait = WebDriverWait(driver, 30)

    def short_wait_for_element(by, value, short_wait=short_wait):
        return short_wait.until(EC.presence_of_element_located((by, value)))
    
    def long_wait_for_element(by, value, long_wait=long_wait):
        return long_wait.until(EC.presence_of_element_located((by, value)))

    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            logger.info(f"attempt {attempt + 1} of {MAX_RETRIES}: navigating to fnet login page...")

            login_url = (os.getenv('LOGIN_URL'))
            driver.get(login_url)

            # login flow
            logger.info("waiting for username field...")
            username_field = long_wait_for_element(By.NAME, "mv_username")

            logger.info("found username field. waiting for password field...")
            password_field = long_wait_for_element(By.NAME, "mv_password")

            logger.info("entering username and password...")
            username_field.send_keys(username)
            password_field.send_keys(password)

            # Find and click the login/submit button
            login_button = short_wait_for_element(By.CLASS_NAME, "login")
            logger.info("Submitting login...")
            login_button.click()

            # Wait for the welcome message indicating a successful login
            logger.info("Waiting for welcome message...")
            welcome_element = short_wait_for_element(By.CSS_SELECTOR, "div.welcome span[role='heading']")

            # If the welcome element is found, login was successful
            if welcome_element and "Welcome" in welcome_element.text:
                logger.info("Login successful.")
            else:
                logger.info("Welcome message not found; login may have failed.")
            return True

        except Exception as e:
            logger.error(f"attempt {attempt + 1} failed: {e}", exc_info=True)
            attempt += 1
            if attempt < MAX_RETRIES:
                logger.info(f"retrying login in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)

    logger.error(f"all {MAX_RETRIES} attempts failed. no more retires.")
    return False