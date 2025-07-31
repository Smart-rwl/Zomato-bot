import pandas as pd
import time
import random
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- CONFIGURATION ---
CSV_PATH = "zomato_profiles.csv"
RESULTS_CSV_PATH = "follow_results.csv"

def setup_driver():
    """Configures the Chrome driver for a headless environment like GitHub Actions."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_with_cookies(driver):
    """Loads session cookies from an environment variable to log in."""
    print("Attempting to log in with session cookies...")
    
    cookies_json = os.getenv("ZOMATO_COOKIES")
    if not cookies_json:
        print("❌ ZOMATO_COOKIES secret not found in environment. Cannot log in.")
        return False

    driver.get("https://www.zomato.com/india")
    time.sleep(2)

    try:
        cookies = json.loads(cookies_json)
        added_cookies_count = 0
        for cookie in cookies:
            # 💡 FINAL FIX: Filter cookies to only use ones for the Zomato domain.
            # This prevents errors from unrelated cookies (e.g., google-analytics).
            if "zomato" not in cookie.get("domain", ""):
                continue  # Skip this cookie and move to the next one

            # Fix for the 'sameSite' attribute issue
            if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                cookie['sameSite'] = "Lax"
            
            driver.add_cookie(cookie)
            added_cookies_count += 1
        
        print(f"✅ Added {added_cookies_count} Zomato-specific cookies.")
        if added_cookies_count == 0:
            print("⚠️ CRITICAL: No Zomato cookies were found or added. Login will fail.")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred while adding cookies: {e}")
        return False

    print("Refreshing page to apply session...")
    driver.refresh()
    time.sleep(random.uniform(3, 5))
    return True

def follow_user(driver, wait, profile_url):
    """Navigates to a user's profile and clicks the follow button if not already following."""
    try:
        print(f"Visiting {profile_url}")
        driver.get(profile_url)
        time.sleep(random.uniform(3, 5))

        try:
            driver.find_element(By.XPATH, '//span[text()="Following"]')
            print(f"☑️ Already following: {profile_url}")
            return "Already Followed"
        except NoSuchElementException:
            pass

        follow_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//span[text()="Follow"]/ancestor::button'))
        )
        follow_button.click()
        print(f"✅ Followed: {profile_url}")
        time.sleep(random.uniform(2, 4))
        return "Success"

    except TimeoutException:
        print(f"❌ Follow button not found on {profile_url}.")
        return "Failure: Button Not Found"
    except Exception as e:
        print(f"⚠️ An unexpected error occurred on {profile_url}: {e}")
        return f"Failure: {e}"

def main():
    """Main function to orchestrate the bot."""
    driver = setup_driver()
    wait = WebDriverWait(driver, 15)

    if not login_with_cookies(driver):
        driver.quit()
        return

    try:
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"❌ Error: The file '{CSV_PATH}' was not found.")
        driver.quit()
        return

    results = []
    for index, row in df.iterrows():
        profile_url = row.get("profile_url")
        if profile_url and isinstance(profile_url, str) and profile_url.startswith("http"):
            status = follow_user(driver, wait, profile_url)
            results.append({"profile_url": profile_url, "status": status})
        else:
            print(f"Skipping invalid URL at row {index}: {profile_url}")
            results.append({"profile_url": profile_url, "status": "Invalid URL"})

    pd.DataFrame(results).to_csv(RESULTS_CSV_PATH, index=False)
    print(f"🎯 All done. Results saved to {RESULTS_CSV_PATH}.")
    driver.quit()

if __name__ == "__main__":
    main()
