"""Installation utilities for crawl4ai-news-fetcher"""
import subprocess
import sys

def install_browsers():
    """Install Playwright browsers"""
    try:
        print("Installing Playwright browsers...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("✅ Playwright Chromium browser installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Playwright browsers: {e}")
        print("Please run manually: playwright install chromium")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    install_browsers()