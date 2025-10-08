import pandas as pd
import time
import random
import json
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# --- CONFIGURATION ---
CSV_PATH = "zomato_profiles.csv"
RESULTS_CSV_PATH = "follow_results.csv"

def setup_driver():
    """
    Configures and initializes an undetected Chrome WebDriver to avoid bot detection.
    """
    print("🚀 Setting up undetected-chromedriver...")
    try:
        options = uc.ChromeOptions()
        # Using --headless=new is the modern way for headless execution
        options.add_argument('--headless=new')
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        driver = uc.Chrome(options=options)
        print("✅ WebDriver setup complete.")
        return driver
    except WebDriverException as e:
        print(f"❌ WebDriver setup failed. Ensure chromedriver is accessible.")
        print(f"Error: {e}")
        return None

def login_with_cookies(driver):
    """
    Loads session cookies from an environment variable to authenticate the session.
    """
    print("🔑 Attempting to log in with session cookies...")
    
    cookies_json = os.getenv("ZOMATO_COOKIES")
    if not cookies_json:
        print("❌ CRITICAL: ZOMATO_COOKIES environment variable not found.")
        return False

    # Navigate to the target domain before adding cookies.
    driver.get("https://www.zomato.com/india")
    
    try:
        cookies = json.loads(cookies_json)
        for cookie in cookies:
            # Selenium's add_cookie is picky about keys. Remove unsupported ones.
            if 'expirationDate' in cookie:
                cookie['expiry'] = int(cookie['expirationDate'])
                del cookie['expirationDate']
            if 'sameSite' in cookie and cookie['sameSite'] not in ["Strict", "Lax", "None"]:
                 del cookie['sameSite']

            try:
                driver.add_cookie(cookie)
            except Exception as e:
                # This might happen if a cookie format is invalid, but we can often proceed.
                print(f"--- ⚠️ Could not add cookie: {cookie.get('name')} | Reason: {e} ---")
                continue
    except json.JSONDecodeError:
        print("❌ CRITICAL: Failed to parse cookies from ZOMATO_COOKIES. Ensure it's valid JSON.")
        return False

    print("🔄 Refreshing page to apply session...")
    driver.refresh()
    
    try:
        # Wait for a unique element that indicates a successful login
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/users/"]'))
        )
        print("✅ Login successful!")
        return True
    except TimeoutException:
        print("❌ Login failed. Profile element not found after loading cookies and refreshing.")
        print("   Please check if your cookies are valid and not expired.")
        return False

def follow_user(driver, wait, profile_url):
    """
    Navigates to a user's profile and clicks the follow button if not already following.
    """
    try:
        print(f"Visiting {profile_url}")
        driver.get(profile_url)

        # Wait for the main profile section to load before checking for buttons
        profile_header_xpath = '//h1[contains(@class, "sc-")]'
        wait.until(EC.presence_of_element_located((By.XPATH, profile_header_xpath)))
        
        # More robustly check for the button's text content.
        # Find the button element first, then check its text.
        follow_button_container_xpath = '//div[contains(@class, "profile-actions")]//button'
        button_element = wait.until(
            EC.presence_of_element_located((By.XPATH, follow_button_container_xpath))
        )
        
        button_text = button_element.text
        if "Following" in button_text:
            print(f"☑️ Already following: {profile_url}")
            return "Already Followed"
        
        elif "Follow" in button_text:
            # Use JavaScript click as a fallback if the standard click is intercepted
            try:
                button_element.click()
            except Exception:
                driver.execute_script("arguments[0].click();", button_element)

            print(f"✅ Followed: {profile_url}")
            time.sleep(random.uniform(1.5, 2.5)) # Small pause after action
            return "Success"
        else:
            print(f"🤷 Button found, but text is neither 'Follow' nor 'Following' ({button_text}).")
            return "Failure: Button text unknown"

    except TimeoutException:
        print(f"❌ Follow button or profile header not found on {profile_url}.")
        return "Failure: Button Not Found"
    except Exception as e:
        print(f"⚠️ An unexpected error occurred on {profile_url}: {e}")
        return f"Failure: {e}"

def main():
    """Main function to orchestrate the bot."""
    driver = setup_driver()
    if not driver:
        return

    try:
        wait = WebDriverWait(driver, 15)

        if not login_with_cookies(driver):
            print("Login process failed. Exiting.")
            return

        try:
            df = pd.read_csv(CSV_PATH)
        except FileNotFoundError:
            print(f"❌ Error: The file '{CSV_PATH}' was not found. Please create it.")
            return

        results = []
        for index, row in df.iterrows():
            profile_url = row.get("profile_url")
            if profile_url and isinstance(profile_url, str) and profile_url.startswith("http"):
                status = follow_user(driver, wait, profile_url)
                results.append({"profile_url": profile_url, "status": status})
                # Add a random delay between actions to mimic human behavior
                time.sleep(random.uniform(3, 6))
            else:
                print(f"Skipping invalid URL at row {index}: {profile_url}")
                results.append({"profile_url": profile_url, "status": "Invalid URL"})
        
        if results:
            pd.DataFrame(results).to_csv(RESULTS_CSV_PATH, index=False)
            print(f"🎯 All done. Results saved to {RESULTS_CSV_PATH}.")
        else:
            print("No URLs were processed.")

    finally:
        print("🔚 Closing WebDriver.")
        driver.quit()

if __name__ == "__main__":
    main()
