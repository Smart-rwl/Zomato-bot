import pandas as pd
import time
import random
import json
import os
# Import the undetected_chromedriver library
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- CONFIGURATION ---
CSV_PATH = "zomato_profiles.csv"
RESULTS_CSV_PATH = "follow_results.csv"

def setup_driver():
    """
    Configures and initializes an undetected Chrome WebDriver to avoid bot detection.
    """
    print("Setting up undetected-chromedriver...")
    options = uc.ChromeOptions()
    # Setting headless mode for undetected-chromedriver is done this way
    options.add_argument('--headless=new')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Initialize the undetected driver
    driver = uc.Chrome(options=options)
    return driver

def login_with_cookies(driver):
    """
    Loads session cookies to authenticate the session. This function remains
    largely the same, but will now work with the undetected driver.
    """
    print("Attempting to log in with session cookies...")
    
    cookies_json = os.getenv("ZOMATO_COOKIES")
    if not cookies_json:
        print("❌ ZOMATO_COOKIES secret not found.")
        return False

    # Navigate to the target domain. This is crucial for setting cookies.
    driver.get("https://www.zomato.com/india")
    time.sleep(3) # Give the page a moment to load with the new driver

    cookies = json.loads(cookies_json)
    added_cookies_count = 0
    for cookie in cookies:
        if "zomato" not in cookie.get("domain", ""):
            continue
        
        # We use the simplified format, letting the browser handle the domain
        formatted_cookie = {
            'name': cookie['name'],
            'value': cookie['value']
        }
        if 'path' in cookie:
            formatted_cookie['path'] = cookie['path']
        if 'secure' in cookie:
            formatted_cookie['secure'] = cookie['secure']
        if 'httpOnly' in cookie:
            formatted_cookie['httpOnly'] = cookie['httpOnly']
        if 'expirationDate' in cookie:
            formatted_cookie['expiry'] = int(cookie['expirationDate'])
        if 'sameSite' in cookie and cookie['sameSite'] in ["Strict", "Lax", "None"]:
             formatted_cookie['sameSite'] = cookie['sameSite']

        try:
            driver.add_cookie(formatted_cookie)
            added_cookies_count += 1
        except Exception as e:
            print(f"--- ⚠️  Could not add cookie: {cookie.get('name')} ---")
            print(f"ERROR: {e}")
            continue
            
    print(f"✅ Attempted to add {added_cookies_count} cookies.")
    if added_cookies_count == 0:
        print("⚠️ CRITICAL: No Zomato cookies were added.")
        return False

    print("Refreshing page to apply session...")
    driver.refresh()
    time.sleep(random.uniform(4, 6))
    
    try:
        driver.find_element(By.CSS_SELECTOR, 'a[href*="/users/"]')
        print("✅ Login successful!")
        return True
    except NoSuchElementException:
        print("❌ Login failed. Profile element not found after loading cookies.")
        return False


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
        print("Login process failed. Exiting.")
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
