import pandas as pd
import time
import random
import json
import os
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# --- CONFIGURATION ---
CSV_PATH = "zomato_profiles.csv"
RESULTS_CSV_PATH = "follow_results.csv"
LOG_FILE_PATH = "bot_activity.log"

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()  # This will also print logs to the console
    ]
)

def setup_driver():
    """Configures and initializes an undetected Chrome WebDriver."""
    logging.info("🚀 Setting up undetected-chromedriver...")
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        # --- FIX APPLIED ---
        # Forcing the driver to match the browser version (140) from the error log.
        driver = uc.Chrome(options=options, version_main=140) 
        
        logging.info("✅ WebDriver setup complete.")
        return driver
    except WebDriverException as e:
        logging.error("❌ WebDriver setup failed. Ensure chromedriver is accessible.")
        logging.error(f"Error: {e}")
        return None

def login_with_cookies(driver):
    """Loads session cookies from an environment variable to authenticate."""
    logging.info("🔑 Attempting to log in with session cookies...")
    
    cookies_json = os.getenv("ZOMATO_COOKIES")
    if not cookies_json:
        logging.critical("❌ ZOMATO_COOKIES environment variable not found.")
        return False

    driver.get("https://www.zomato.com/india")
    
    try:
        cookies = json.loads(cookies_json)
        for cookie in cookies:
            if 'expirationDate' in cookie:
                cookie['expiry'] = int(cookie['expirationDate'])
                del cookie['expirationDate']
            if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                 del cookie['sameSite']
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logging.warning(f"--- Could not add cookie: {cookie.get('name')} | Reason: {e} ---")
    except json.JSONDecodeError:
        logging.critical("❌ Failed to parse cookies from ZOMATO_COOKIES. Ensure it's valid JSON.")
        return False

    logging.info("🔄 Refreshing page to apply session...")
    driver.refresh()
    
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/users/"]')))
        logging.info("✅ Login successful!")
        return True
    except TimeoutException:
        logging.error("❌ Login failed. Profile element not found after loading cookies.")
        logging.error("   Please check if your cookies are valid and not expired.")
        return False

def follow_user(driver, wait, profile_url):
    """Navigates to a user's profile and clicks the follow button if not already following."""
    try:
        logging.info(f"Visiting {profile_url}")
        driver.get(profile_url)

        # Wait for a stable element like the user's name to ensure the page is loaded
        wait.until(EC.presence_of_element_located((By.XPATH, '//h1')))
        
        # More robustly check for the button's text content.
        button_xpath = '//button[div/span[text()="Follow"]] | //button[div/span[text()="Following"]]'
        button_element = wait.until(EC.presence_of_element_located((By.XPATH, button_xpath)))
        
        button_text = button_element.text
        if "Following" in button_text:
            logging.info(f"☑️ Already following: {profile_url}")
            return "Already Followed"
        
        elif "Follow" in button_text:
            driver.execute_script("arguments[0].click();", button_element)
            logging.info(f"✅ Followed: {profile_url}")
            time.sleep(random.uniform(1.5, 2.5))
            return "Success"
        else:
            logging.warning(f"🤷 Button found, but text is neither 'Follow' nor 'Following' ({button_text}).")
            return "Failure: Button text unknown"

    except TimeoutException:
        logging.error(f"❌ Follow button or profile header not found on {profile_url}.")
        return "Failure: Button Not Found"
    except Exception as e:
        logging.error(f"⚠️ An unexpected error occurred on {profile_url}: {e}")
        return f"Failure: {e}"

def main():
    """Main function to orchestrate the bot."""
    driver = setup_driver()
    if not driver:
        return

    try:
        wait = WebDriverWait(driver, 15)
        if not login_with_cookies(driver):
            logging.critical("Login process failed. Exiting.")
            return

        try:
            df = pd.read_csv(CSV_PATH)
        except FileNotFoundError:
            logging.critical(f"❌ Error: The file '{CSV_PATH}' was not found. Please create it.")
            return

        results = []
        for index, row in df.iterrows():
            profile_url = row.get("profile_url")
            if profile_url and isinstance(profile_url, str) and profile_url.startswith("http"):
                status = follow_user(driver, wait, profile_url)
                results.append({"profile_url": profile_url, "status": status})
                time.sleep(random.uniform(3, 6))
            else:
                logging.warning(f"Skipping invalid URL at row {index}: {profile_url}")
                results.append({"profile_url": profile_url, "status": "Invalid URL"})
        
        if results:
            pd.DataFrame(results).to_csv(RESULTS_CSV_PATH, index=False)
            logging.info(f"🎯 All done. Results saved to {RESULTS_CSV_PATH}.")
        else:
            logging.info("No URLs were processed.")

    finally:
        logging.info("🔚 Closing WebDriver.")
        driver.quit()

if __name__ == "__main__":
    main()
