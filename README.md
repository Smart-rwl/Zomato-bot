
# Zomato Follower Bot

This is a Python bot that automates following users on Zomato based on a list of profile URLs. It uses Selenium and undetected-chromedriver to avoid bot detection and is designed to be run automatically using GitHub Actions.

## ✨ Features

- Logs into Zomato using session cookies (no password required).
- Reads a list of user profiles from a CSV file.
- Checks if a user is already followed and skips if so.
- Follows users with randomized delays to mimic human behavior.
- Saves the results of its actions to a new CSV file.
- Can be run on a schedule automatically with GitHub Actions.

## 🚀 Setup and Usage

### 1. Clone the Repository
```bash
git clone [https://github.com/Smart-rwl/Zomato-bot.git](https://github.com/Smart-rwl/Zomato-bot.git)
cd Zomato-bot
