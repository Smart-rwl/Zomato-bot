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
# The CSV path is now relative to the script's location
CSV_PATH = "zomato_profiles.csv"
RESULTS_CSV_PATH = "follow_results.csv"

def setup_driver():
    """Configures the Chrome driver for GitHub Actions."""
    chrome_options = Options()
    # IMPORTANT: These options are required to run in a headless environment like GitHub Actions
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Let Selenium manage the driver automatically
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_with_cookies(driver):
    """Loads session cookies from an environment variable to log in."""
    print("Attempting to log in with session cookies...")
    
    # Get cookies from the environment variable set by GitHub Secrets
    cookies_json = os.getenv("ZOMATO_COOKIES")
    if not cookies_json:
        print("❌ ZOMATO_COOKIES secret not found in environment. Cannot log in.")
        return False

    # Zomato requires you to be on the domain before adding cookies.
    # We go to a non-sensitive page first.
    driver.get("https://www.zomato.com/india")
    time.sleep(2) # Allow page to settle

    try:
        cookies = json.loads(cookies_json)
        for cookie in cookies:
            driver.add_cookie(cookie)
    except json.JSONDecodeError:
        print("❌ Failed to decode cookies. Make sure the secret is a valid JSON string.")
        return False

    print("✅ Cookies loaded successfully. Refreshing page to apply session.")
    driver.refresh()
    time.sleep(random.uniform(3, 5)) # Wait for refresh to take effect
    return True

def follow_user(driver, wait, profile_url):
    """Navigates to a user's profile and clicks the follow button."""
    try:
        print(f"Visiting {profile_url}")
        driver.get(profile_url)
        time.sleep(random.uniform(3, 5))  # Let page render JS

        # 1. Check if already following
        try:
            driver.find_element(By.XPATH, '//span[text()="Following"]')
            print(f"☑️ Already following: {profile_url}")
            return "Already Followed"
        except NoSuchElementException:
            # Not following yet, proceed to find the 'Follow' button
            pass

        # 2. Find and click the 'Follow' button
        follow_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//span[text()="Follow"]/ancestor::button'))
        )
        follow_button.click()
        print(f"✅ Followed: {profile_url}")
        time.sleep(random.uniform(2, 4))
        return "Success"

    except TimeoutException:
        print(f"❌ Follow button not found on {profile_url}. The user may be private or page didn't load correctly.")
        return "Failure: Button Not Found"
    except Exception as e:
        print(f"⚠️ An unexpected error occurred on {profile_url}: {e}")
        return f"Failure: {e}"

def main():
    """Main function to orchestrate the bot."""
    driver = setup_driver()
    wait = WebDriverWait(driver, 15) # Increased wait time for robustness

    if not login_with_cookies(driver):
        driver.quit()
        return

    try:
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"❌ Error: The file '{CSV_PATH}' was not found. Make sure it exists.")
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

    # Save results to a new CSV
    pd.DataFrame(results).to_csv(RESULTS_CSV_PATH, index=False)
    print(f"🎯 All done. Results saved to {RESULTS_CSV_PATH}.")
    driver.quit()

if __name__ == "__main__":
    main()